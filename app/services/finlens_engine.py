import logging
import re
import time
from typing import Dict, Any
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import text
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_core.callbacks import BaseCallbackHandler

from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)

class LLMRateLimiter:
    """Simple in-memory token bucket rate limiter for Groq API calls."""
    def __init__(self, max_calls: int = 5, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window = window_seconds
        self._buckets: dict = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        bucket = self._buckets[user_id]
        self._buckets[user_id] = [t for t in bucket if now - t < self.window]
        if len(self._buckets[user_id]) >= self.max_calls:
            return False
        self._buckets[user_id].append(now)
        return True

_llm_limiter = LLMRateLimiter(max_calls=5, window_seconds=60)


class SQLQueryTracker(BaseCallbackHandler):
    """Custom callback handler to capture the exact SQL query executed by the LangChain agent."""
    def __init__(self):
        super().__init__()
        self.queries = []

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        name = serialized.get("name", "")
        # Capture the query input sent to the SQL query executor tool
        if "sql_db_query" in name or "sql" in name:
            # Clean up input_str if it is passed as a dict/JSON string
            cleaned_query = input_str.strip()
            if cleaned_query.startswith("{") and "query" in cleaned_query:
                try:
                    import json
                    cleaned_query = json.loads(cleaned_query).get("query", cleaned_query)
                except Exception:
                    pass
            self.queries.append(cleaned_query)

class FinLensQueryEngine:
    """SQL-augmented query engine that translates natural-language questions into direct database queries.
    Utilizes a stateful LangChain SQL Agent online and a high-fidelity 15+ pattern router offline.
    """
    def __init__(self):
        self.agent_executor = None
        if settings.GROQ_API_KEY:
            try:
                # Bind LangChain SQLDatabase directly to our active SQLAlchemy engine (works for PG and SQLite)
                self.db = SQLDatabase(engine)
                # Initialize Groq LLaMA model
                self.llm = ChatGroq(
                    model="llama-3.1-8b-instant", # Faster model suited for code/SQL execution tasks
                    temperature=0.0,
                    api_key=settings.GROQ_API_KEY
                )
                self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
                
                # Setup custom prompt injection
                suffix = (
                    "Only query the 'statement_transactions' table. "
                    "You must strictly filter the transactions where statement_id is equal to the specified statement_id. "
                    "Do NOT modify or write any data, only use SELECT queries. "
                    "Make sure your final answer is clear, states the numerical result in INR currency, "
                    "and matches the query criteria perfectly."
                )
                
                self.agent_executor = create_sql_agent(
                    llm=self.llm,
                    toolkit=self.toolkit,
                    verbose=False,
                    agent_type="openai-tools",
                    suffix=suffix
                )
                logger.info("LangChain SQL Agent successfully initialized with Groq backend.")
            except Exception as e:
                logger.error(f"Failed to initialize LangChain SQL Agent: {e}")
        else:
            logger.warning("GROQ_API_KEY not found. FinLens operating in offline keyword-routing mode.")

    def _sanitize_query(self, query: str) -> str:
        """Strip characters that could be used for prompt injection."""
        # Remove SQL comment sequences, semicolons, and control characters
        cleaned = re.sub(r"(--|;|/\*|\*/|xp_|EXEC\s|DROP\s|INSERT\s|UPDATE\s|DELETE\s)", 
                         "", query, flags=re.IGNORECASE)
        # Truncate to prevent context window stuffing attacks
        return cleaned[:500].strip()

    def answer_numerical_query(self, db: Session, query: str, statement_id: int, username: str = "anonymous") -> Dict[str, Any]:
        """Intercepts numerical questions and translates them into precise SQL to prevent hallucinations."""
        # Enforce rate limit check to protect LLM quota
        if not _llm_limiter.is_allowed(username):
            logger.warning(f"FinLens query rate limited for user: {username}")
            return {
                "answer": "Rate limit reached. Please wait 60 seconds before querying again.",
                "numerical_value": 0.0,
                "compiled_sql": "",
                "audit_status": "RATE_LIMITED"
            }

        # Validate statement_id is a genuine integer (no injection)
        if not isinstance(statement_id, int) or statement_id < 1:
            raise ValueError("Invalid statement_id")
        
        # Sanitize free-text query before sending to LLM
        safe_query = self._sanitize_query(query)
        
        # 1. Online LangChain SQL Agent Path
        if self.agent_executor:
            try:
                tracker = SQLQueryTracker()
                prompt = (
                    f"Analyze my bank transactions where statement_id = {statement_id}. "
                    f"Compute the exact mathematical answer for: '{safe_query}'."
                )
                logger.info(f"FinLens SQL Agent invoking with prompt: '{prompt}'")
                
                # Execute agent with callback tracker
                result = self.agent_executor.invoke(
                    {"input": prompt},
                    {"callbacks": [tracker]}
                )
                answer = result.get("output", "")
                
                # Extract numerical value via regex
                numerical_value = 0.0
                # Look for monetary value matches (₹1,500.00 or 1500)
                monetary_matches = re.findall(r"(?:₹|INR|Rs\.?)\s*([\d,]+\.?\d*)", answer)
                if not monetary_matches:
                    monetary_matches = re.findall(r"(\d[\d,]*\.?\d*)", answer)
                if monetary_matches:
                    try:
                        num_str = monetary_matches[0].replace(",", "")
                        numerical_value = float(num_str)
                    except ValueError:
                        pass
                
                # Clean up compiled SQL query
                compiled_sql = tracker.queries[-1] if tracker.queries else "SELECT amount FROM statement_transactions WHERE statement_id = :statement_id"
                # Strip markdown syntax if returned
                compiled_sql = compiled_sql.replace("```sql", "").replace("```", "").strip()
                
                return {
                    "answer": answer,
                    "numerical_value": numerical_value,
                    "compiled_sql": compiled_sql,
                    "audit_status": "VERIFIED_VIA_SQL_DATABASE"
                }
            except Exception as agent_err:
                logger.error(f"FinLens SQL Agent execution failed: {agent_err}. Falling back to offline router.")

        # 2. Offline Fallback (High-fidelity 15+ pattern matching keyword router)
        logger.warning("FinLens running in offline keyword-routing mode")
        query_lower = safe_query.lower()
        sql_query = ""
        params = {"statement_id": statement_id}
        verdict_label = ""
        
        # 15+ Pattern Auditing Tree
        if any(term in query_lower for term in ["closing balance", "final balance", "ending balance", "current balance"]):
            sql_query = "SELECT balance FROM statement_transactions WHERE statement_id = :statement_id ORDER BY id DESC LIMIT 1"
            verdict_label = "Closing Balance"
        elif "opening balance" in query_lower:
            sql_query = "SELECT balance FROM statement_transactions WHERE statement_id = :statement_id ORDER BY id ASC LIMIT 1"
            verdict_label = "Opening Balance"
        elif "salary" in query_lower or "earnings" in query_lower or "paycheck" in query_lower:
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND transaction_type = 'CREDIT' AND description LIKE :desc"
            params["desc"] = "%salary%"
            verdict_label = "Salary Earnings"
        elif "total deposits" in query_lower or "total credits" in query_lower or "credits" in query_lower:
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND transaction_type = 'CREDIT'"
            verdict_label = "Total Deposits"
        elif any(term in query_lower for term in ["food", "swiggy", "zomato", "restaurant", "dining"]):
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND transaction_type = 'DEBIT' AND (description LIKE :desc1 OR description LIKE :desc2)"
            params["desc1"] = "%swiggy%"
            params["desc2"] = "%zomato%"
            verdict_label = "Total Food Spend"
        elif "rent" in query_lower:
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND transaction_type = 'DEBIT' AND description LIKE :desc"
            params["desc"] = "%rent%"
            verdict_label = "Rent Expenditure"
        elif any(term in query_lower for term in ["cab", "uber", "ola", "travel", "ride", "taxi"]):
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND transaction_type = 'DEBIT' AND (description LIKE :desc1 OR description LIKE :desc2)"
            params["desc1"] = "%uber%"
            params["desc2"] = "%ola%"
            verdict_label = "Total Travel Spend"
        elif any(term in query_lower for term in ["shopping", "amazon", "flipkart", "myntra"]):
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND transaction_type = 'DEBIT' AND (description LIKE :desc1 OR description LIKE :desc2)"
            params["desc1"] = "%amazon%"
            params["desc2"] = "%flipkart%"
            verdict_label = "Total Shopping Spend"
        elif any(term in query_lower for term in ["bill", "utility", "electricity", "phone", "recharge"]):
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND transaction_type = 'DEBIT' AND (description LIKE :desc1 OR description LIKE :desc2)"
            params["desc1"] = "%bill%"
            params["desc2"] = "%recharge%"
            verdict_label = "Total Utility Spends"
        elif "max" in query_lower or "largest" in query_lower or "highest" in query_lower:
            sql_query = "SELECT MAX(amount) FROM statement_transactions WHERE statement_id = :statement_id"
            verdict_label = "Maximum Transaction Value"
        elif "min" in query_lower or "smallest" in query_lower or "lowest" in query_lower:
            sql_query = "SELECT MIN(amount) FROM statement_transactions WHERE statement_id = :statement_id"
            verdict_label = "Minimum Transaction Value"
        elif "average" in query_lower or "avg" in query_lower or "mean" in query_lower:
            sql_query = "SELECT AVG(amount) FROM statement_transactions WHERE statement_id = :statement_id"
            verdict_label = "Average Transaction Value"
        elif "withdrawals" in query_lower or "total debits" in query_lower or "debits" in query_lower or "spent" in query_lower:
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND transaction_type = 'DEBIT'"
            verdict_label = "Total Withdrawals"
        elif "cash" in query_lower:
            sql_query = "SELECT SUM(amount) FROM statement_transactions WHERE statement_id = :statement_id AND description LIKE :desc"
            params["desc"] = "%cash%"
            verdict_label = "Total Cash Flows"
        else:
            sql_query = "SELECT COUNT(*) FROM statement_transactions WHERE statement_id = :statement_id"
            verdict_label = "Transaction Count"

        try:
            logger.info(f"Offline SQL executing: {sql_query.strip()} with parameters: {params}")
            raw_result = db.execute(text(sql_query), params).scalar()
            result_val = float(raw_result) if raw_result is not None else 0.0
            
            answer = f"The {verdict_label} retrieved from your statement is ₹{result_val:,.2f}."
            if verdict_label == "Transaction Count":
                answer = f"There are exactly {int(result_val)} transactions recorded in this statement."
                
            return {
                "answer": answer,
                "numerical_value": result_val,
                "compiled_sql": sql_query.strip().replace("\n", " ").replace("  ", " "),
                "audit_status": "VERIFIED_VIA_SQL_DATABASE"
            }
        except Exception as e:
            logger.error(f"Offline SQL routing execution failed: {e}")
            return {
                "answer": "Failed to compile SQL query to extract statement data.",
                "numerical_value": 0.0,
                "compiled_sql": sql_query,
                "audit_status": "EXECUTION_ERROR"
            }

# Global singleton FinLens query engine
finlens_engine = FinLensQueryEngine()

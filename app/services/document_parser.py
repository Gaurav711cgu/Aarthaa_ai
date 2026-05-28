import re
from sqlalchemy.orm import Session
from app.models.statement import BankStatement, StatementTransaction
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class BankStatementParser:
    """Intelligent parsing engine that digests digital bank statements.
    Extracts transaction tables and metadata and commits them to SQL tables.
    """
    def __init__(self):
        pass

    def parse_and_store_statement(self, db: Session, raw_text: str) -> Dict[str, Any]:
        """Parses raw text bank statements, calculates totals, and saves to database."""
        logger.info("Starting statement parsing pipeline...")
        
        # 1. Parse Metadata using regex
        bank_name_match = re.search(r"BANK:\s*([^\n]+)", raw_text, re.IGNORECASE)
        account_match = re.search(r"ACCOUNT:\s*([A-Za-z0-9]+)", raw_text, re.IGNORECASE)
        period_match = re.search(r"PERIOD:\s*([^\n]+)", raw_text, re.IGNORECASE)
        
        bank_name = bank_name_match.group(1).strip() if bank_name_match else "Unspecified Bank"
        account_number = account_match.group(1).strip() if account_match else "000000000000"
        statement_period = period_match.group(1).strip() if period_match else "Unknown Period"
        
        # 2. Extract Transactions
        # Line format: YYYY-MM-DD | Description | CREDIT/DEBIT | Amount | Balance
        tx_lines = re.findall(r"(\d{4}-\d{2}-\d{2})\s*\|\s*([^\|]+)\|\s*(CREDIT|DEBIT)\s*\|\s*([\d\.]+)\s*\|\s*([\d\.]+)", raw_text, re.IGNORECASE)
        
        total_deposits = 0.0
        total_withdrawals = 0.0
        ending_balance = 0.0
        
        parsed_transactions = []
        for match in tx_lines:
            tx_date, description, tx_type, amount_str, balance_str = match
            amount = float(amount_str)
            balance = float(balance_str)
            
            tx_type_upper = tx_type.upper()
            if tx_type_upper == "CREDIT":
                total_deposits += amount
            elif tx_type_upper == "DEBIT":
                total_withdrawals += amount
                
            ending_balance = balance # Last transaction sets ending balance
            
            parsed_transactions.append({
                "date": tx_date.strip(),
                "description": description.strip(),
                "transaction_type": tx_type_upper,
                "amount": amount,
                "balance": balance
            })
            
        logger.info(f"Parsed metadata: Bank={bank_name}, Account={account_number}, Transactions={len(parsed_transactions)}")
        
        # 3. Save to database using SQL Session
        statement_record = BankStatement(
            account_number=account_number,
            bank_name=bank_name,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            ending_balance=ending_balance,
            statement_period=statement_period
        )
        
        db.add(statement_record)
        db.flush() # Fetch statement ID
        
        db_transactions = []
        for tx in parsed_transactions:
            tx_record = StatementTransaction(
                statement_id=statement_record.id,
                date=tx["date"],
                description=tx["description"],
                transaction_type=tx["transaction_type"],
                amount=tx["amount"],
                balance=tx["balance"]
            )
            db.add(tx_record)
            db_transactions.append(tx_record)
            
        db.commit()
        logger.info(f"Statement committed successfully. Assigned ID={statement_record.id}")
        
        return {
            "statement_id": statement_record.id,
            "bank_name": bank_name,
            "account_number": account_number,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "ending_balance": ending_balance,
            "transaction_count": len(parsed_transactions)
        }

# Global singleton statement parser
statement_parser = BankStatementParser()

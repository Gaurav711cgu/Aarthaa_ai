import re
import io
import logging
from typing import Dict, Any
import pandas as pd
from sqlalchemy.orm import Session
from app.models.statement import BankStatement, StatementTransaction

logger = logging.getLogger(__name__)

class BankStatementParser:
    """Intelligent parsing engine that digests digital bank statements.
    Extracts transaction tables and metadata and commits them to SQL tables.
    Supports raw text files and automated CSV parsing with columns normalization.
    """
    def __init__(self):
        pass

    def parse_and_store_statement(self, db: Session, raw_text: str, owner_username: str = "anonymous") -> Dict[str, Any]:
        """Parses raw text or CSV bank statements, normalizes columns, and saves to database."""
        logger.info("Starting statement parsing pipeline...")
        
        # 1. Parse Metadata using regex
        bank_name_match = re.search(r"BANK:\s*([^\n]+)", raw_text, re.IGNORECASE)
        account_match = re.search(r"ACCOUNT:\s*([A-Za-z0-9]+)", raw_text, re.IGNORECASE)
        period_match = re.search(r"PERIOD:\s*([^\n]+)", raw_text, re.IGNORECASE)
        
        bank_name = bank_name_match.group(1).strip() if bank_name_match else "Unspecified Bank"
        account_number = account_match.group(1).strip() if account_match else "000000000000"
        statement_period = period_match.group(1).strip() if period_match else "Unknown Period"
        
        total_deposits = 0.0
        total_withdrawals = 0.0
        ending_balance = 0.0
        parsed_transactions = []

        # 2. Identify if raw_text contains CSV structure
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        # Filter metadata lines (lines containing BANK:, ACCOUNT:, PERIOD:)
        csv_lines = [line for line in lines if not re.match(r"^(BANK|ACCOUNT|PERIOD):", line, re.IGNORECASE)]

        csv_text = "\n".join(csv_lines)

        # A text is likely CSV if it contains commas and lacks vertical bars
        is_csv = "," in csv_text and "|" not in csv_text

        if is_csv:
            logger.info("FinLens identified CSV format. Commencing Pandas normalization parser...")
            try:
                # Load CSV using pandas
                df = pd.read_csv(io.StringIO(csv_text))
                
                # Strip spaces from column names
                df.columns = [col.strip() for col in df.columns]
                
                # Column mapping finder helper
                date_col = next((c for c in df.columns if any(k in c.lower() for k in ["date", "time"])), None)
                desc_col = next((c for c in df.columns if any(k in c.lower() for k in ["description", "narration", "particular", "merchant"])), None)
                type_col = next((c for c in df.columns if any(k in c.lower() for k in ["type", "cr/dr", "dr/cr", "credit/debit", "direction"])), None)
                amount_col = next((c for c in df.columns if any(k in c.lower() for k in ["amount", "value", "tx_amount", "sum"])), None)
                balance_col = next((c for c in df.columns if any(k in c.lower() for k in ["balance", "bal", "ending_balance"])), None)

                # Fallback to defaults if column mapping fails
               if not date_col and len(df.columns) > 0:
    date_col = df.columns[0]
if not desc_col and len(df.columns) > 1:
    desc_col = df.columns[1]
if not type_col and len(df.columns) > 2:
    type_col = df.columns[2]
if not amount_col and len(df.columns) > 3:
    amount_col = df.columns[3]
if not balance_col and len(df.columns) > 4:
    balance_col = df.columns[4]

                logger.info(f"CSV Columns mapped: Date='{date_col}', Desc='{desc_col}', Type='{type_col}', Amount='{amount_col}', Bal='{balance_col}'")

                for _, row in df.iterrows():
                    tx_date = str(row.get(date_col, "2026-03-01")).strip()
                    description = str(row.get(desc_col, "Transaction")).strip()
                    raw_amount = row.get(amount_col, 0.0)
                    
                    try:
                        amount = abs(float(str(raw_amount).replace(",", "")))
                    except ValueError:
                        amount = 0.0
                        
                    balance = 0.0
                    if balance_col in df.columns:
                        try:
                            balance = float(str(row.get(balance_col, 0.0)).replace(",", ""))
                        except ValueError:
                            pass

                    # Normalization rules for credit/debit transaction type
                    raw_type = str(row.get(type_col, "")).upper().strip() if type_col else ""
                    tx_type = "DEBIT" # default
                    
                    # If type is indicated by positive/negative amount
                    if float(str(raw_amount).replace(",", "")) > 0.0 and not raw_type:
                        tx_type = "CREDIT"
                    elif float(str(raw_amount).replace(",", "")) < 0.0 and not raw_type:
                        tx_type = "DEBIT"
                    # If type is explicitly stated
                    elif any(k in raw_type for k in ["CR", "CREDIT", "+", "C"]):
                        tx_type = "CREDIT"
                    elif any(k in raw_type for k in ["DR", "DEBIT", "-", "D"]):
                        tx_type = "DEBIT"

                    if tx_type == "CREDIT":
                        total_deposits += amount
                    else:
                        total_withdrawals += amount
                    ending_balance = balance

                    parsed_transactions.append({
                        "date": tx_date,
                        "description": description,
                        "transaction_type": tx_type,
                        "amount": amount,
                        "balance": balance
                    })
            except Exception as pandas_err:
                logger.error(f"Pandas CSV parsing failed: {pandas_err}. Falling back to regex parser.")
                is_csv = False

        if not is_csv:
            # Fallback to original vertical-bar regex parser for logs
            logger.info("FinLens executing pipe-delimited parser...")
            tx_lines = re.findall(
                r"(\d{4}-\d{2}-\d{2})\s*\|\s*([^\|]+)\|\s*(CREDIT|DEBIT|CR|DR|DR\/CR|CR\/DR)\s*\|\s*([\d\.]+)\s*\|\s*([\d\.]+)", 
                raw_text, 
                re.IGNORECASE
            )
            
            for match in tx_lines:
                tx_date, description, tx_type, amount_str, balance_str = match
                amount = float(amount_str)
                balance = float(balance_str)
                
                # Normalize types in regex parser
                tx_type_upper = tx_type.upper().strip()
                if any(k in tx_type_upper for k in ["CREDIT", "CR"]):
                    tx_type_norm = "CREDIT"
                    total_deposits += amount
                else:
                    tx_type_norm = "DEBIT"
                    total_withdrawals += amount
                    
                ending_balance = balance # Last transaction sets ending balance
                
                parsed_transactions.append({
                    "date": tx_date.strip(),
                    "description": description.strip(),
                    "transaction_type": tx_type_norm,
                    "amount": amount,
                    "balance": balance
                })

        logger.info(f"Parsed metadata: Bank={bank_name}, Account={account_number}, Transactions={len(parsed_transactions)}")
        
        # 3. Save to database using SQL Session
        statement_record = BankStatement(
            owner_username=owner_username,
            account_number=account_number,
            bank_name=bank_name,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            ending_balance=ending_balance,
            statement_period=statement_period
        )
        
        db.add(statement_record)
        db.flush() # Fetch statement ID
        
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

import json
import sqlite3
import os
from typing import Optional, List, Dict, Any
from app.repositories.base import BaseRepository

class FraudTransactionRepository(BaseRepository[Dict[str, Any]]):
    """Fraud Transaction Repository pattern implementation with SQLite persistence.
    Decouples database operations from route handlers and supports in-memory or on-disk SQLite.
    """
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS fraud_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    amount REAL,
                    user_id TEXT,
                    risk_score REAL,
                    payload_json TEXT
                )
            """)

    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT payload_json FROM fraud_transactions WHERE transaction_id = ?", (entity_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None

    def list_all(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT payload_json FROM fraud_transactions")
        rows = cursor.fetchall()
        return [json.loads(r[0]) for r in rows]

    def add(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        tx_id = str(entity.get("transaction_id", f"tx_{int(len(self.list_all()) + 1)}"))
        entity["transaction_id"] = tx_id
        amount = float(entity.get("amount", entity.get("TransactionAmt", 0.0)))
        user_id = str(entity.get("user_id", "anonymous"))
        risk_score = float(entity.get("risk_score", 0.0))
        payload_str = json.dumps(entity)

        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO fraud_transactions (transaction_id, amount, user_id, risk_score, payload_json)
                VALUES (?, ?, ?, ?, ?)
            """, (tx_id, amount, user_id, risk_score, payload_str))
        return entity

    def remove(self, entity_id: str) -> bool:
        with self.conn:
            cursor = self.conn.execute("DELETE FROM fraud_transactions WHERE transaction_id = ?", (entity_id,))
            return cursor.rowcount > 0

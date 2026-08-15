from typing import Optional, List, Dict, Any
from app.repositories.base import BaseRepository

class FraudTransactionRepository(BaseRepository[Dict[str, Any]]):
    """Fraud Transaction Repository pattern implementation.
    Decouples database operations (PostgreSQL / SQLite / In-Memory Mock) from route handlers.
    """
    def __init__(self, db_session: Optional[Any] = None):
        self.db_session = db_session
        self._mock_storage: Dict[str, Dict[str, Any]] = {}

    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self._mock_storage.get(entity_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._mock_storage.values())

    def add(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        tx_id = entity.get("transaction_id", f"tx_{len(self._mock_storage) + 1}")
        entity["transaction_id"] = tx_id
        self._mock_storage[tx_id] = entity
        return entity

    def remove(self, entity_id: str) -> bool:
        if entity_id in self._mock_storage:
            del self._mock_storage[entity_id]
            return True
        return False

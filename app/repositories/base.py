from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Any

T = TypeVar("T")

class BaseRepository(ABC, Generic[T]):
    """Abstract Base Repository pattern interface decoupling FastAPI route handlers from database engine details."""
    
    @abstractmethod
    def get_by_id(self, entity_id: Any) -> Optional[T]:
        pass

    @abstractmethod
    def list_all(self) -> List[T]:
        pass

    @abstractmethod
    def add(self, entity: T) -> T:
        pass

    @abstractmethod
    def remove(self, entity_id: Any) -> bool:
        pass

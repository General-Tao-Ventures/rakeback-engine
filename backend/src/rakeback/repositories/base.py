"""Base repository with common CRUD operations."""

from typing import Generic, TypeVar, Type, Optional, Sequence
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from rakeback.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Base repository providing common CRUD operations.
    
    All repositories should inherit from this class and specify
    their model type.
    """
    
    model: Type[T]
    
    def __init__(self, session: Session):
        """Initialize repository with database session."""
        self.session = session
    
    def get_by_id(self, id: str) -> Optional[T]:
        """Get a single record by ID."""
        return self.session.get(self.model, id)
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> Sequence[T]:
        """Get all records with optional pagination."""
        stmt = select(self.model).offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return self.session.scalars(stmt).all()
    
    def count(self) -> int:
        """Count all records."""
        stmt = select(func.count()).select_from(self.model)
        return self.session.scalar(stmt) or 0
    
    def add(self, entity: T) -> T:
        """Add a new entity to the session."""
        self.session.add(entity)
        self.session.flush()
        return entity
    
    def add_all(self, entities: Sequence[T]) -> Sequence[T]:
        """Add multiple entities to the session."""
        self.session.add_all(entities)
        self.session.flush()
        return entities
    
    def delete(self, entity: T) -> None:
        """Delete an entity from the session."""
        self.session.delete(entity)
        self.session.flush()
    
    def exists(self, id: str) -> bool:
        """Check if a record exists by ID."""
        return self.get_by_id(id) is not None

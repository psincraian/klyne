from abc import ABC
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType], ABC):
    """
    Base repository class providing common CRUD operations.
    """

    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[ModelType]:
        """Get all records with optional pagination."""
        query = select(self.model)
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, obj_data: Dict[str, Any]) -> ModelType:
        """Create a new record."""
        obj = self.model(**obj_data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, id: int, obj_data: Dict[str, Any]) -> Optional[ModelType]:
        """Update a record by ID."""
        await self.db.execute(
            update(self.model)
            .filter(self.model.id == id)
            .values(**obj_data)
        )
        return await self.get_by_id(id)

    async def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        result = await self.db.execute(
            delete(self.model).filter(self.model.id == id)
        )
        return result.rowcount > 0

    async def exists(self, id: int) -> bool:
        """Check if a record exists by ID."""
        result = await self.db.execute(
            select(self.model.id).filter(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        """Count total records."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(self.model.id))
        )
        return result.scalar()
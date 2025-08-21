from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key import APIKey
from src.repositories.base import BaseRepository


class APIKeyRepository(BaseRepository[APIKey]):
    """Repository for APIKey model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, APIKey)

    async def get_by_key(self, key: str) -> Optional[APIKey]:
        """Get API key by key value."""
        result = await self.db.execute(
            select(APIKey).filter(APIKey.key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> List[APIKey]:
        """Get all API keys for a user."""
        result = await self.db.execute(
            select(APIKey).filter(APIKey.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_package_name(self, package_name: str) -> List[APIKey]:
        """Get all API keys for a specific package."""
        result = await self.db.execute(
            select(APIKey).filter(APIKey.package_name == package_name)
        )
        return list(result.scalars().all())

    async def get_by_user_and_package(self, user_id: int, package_name: str) -> Optional[APIKey]:
        """Get API key for a specific user and package combination."""
        result = await self.db.execute(
            select(APIKey).filter(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.package_name == package_name
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_api_key(self, user_id: int, package_name: str, key: str, 
                            description: Optional[str] = None) -> APIKey:
        """Create a new API key."""
        return await self.create({
            "user_id": user_id,
            "package_name": package_name,
            "key": key,
            "description": description,
            "is_active": True
        })

    async def get_active_keys_by_user(self, user_id: int) -> List[APIKey]:
        """Get all active API keys for a user."""
        result = await self.db.execute(
            select(APIKey).filter(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.is_active
                )
            )
        )
        return list(result.scalars().all())

    async def get_active_keys_by_package(self, package_name: str) -> List[APIKey]:
        """Get all active API keys for a package."""
        result = await self.db.execute(
            select(APIKey).filter(
                and_(
                    APIKey.package_name == package_name,
                    APIKey.is_active
                )
            )
        )
        return list(result.scalars().all())

    async def deactivate_key(self, key_id: int) -> Optional[APIKey]:
        """Deactivate an API key."""
        return await self.update(key_id, {"is_active": False})

    async def activate_key(self, key_id: int) -> Optional[APIKey]:
        """Activate an API key."""
        return await self.update(key_id, {"is_active": True})

    async def key_exists(self, key: str) -> bool:
        """Check if an API key exists."""
        result = await self.db.execute(
            select(APIKey.id).filter(APIKey.key == key)
        )
        return result.scalar_one_or_none() is not None

    async def user_has_package_key(self, user_id: int, package_name: str) -> bool:
        """Check if a user already has an API key for a specific package."""
        result = await self.db.execute(
            select(APIKey.id).filter(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.package_name == package_name
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_packages_for_user(self, user_id: int) -> List[str]:
        """Get all unique package names for a user's API keys."""
        result = await self.db.execute(
            select(APIKey.package_name).filter(APIKey.user_id == user_id).distinct()
        )
        return [package for package in result.scalars().all()]

    async def count_keys_by_user(self, user_id: int) -> int:
        """Count total API keys for a user."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(APIKey.id)).filter(APIKey.user_id == user_id)
        )
        return result.scalar()

    async def count_active_keys_by_user(self, user_id: int) -> int:
        """Count active API keys for a user."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(APIKey.id)).filter(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.is_active
                )
            )
        )
        return result.scalar()

    async def get_user_api_keys_with_filter(self, user_id: int, package_name: Optional[str] = None) -> List[APIKey]:
        """Get user's API keys with optional package filter."""
        query = select(APIKey).filter(APIKey.user_id == user_id)
        
        if package_name:
            query = query.filter(APIKey.package_name == package_name)
            
        result = await self.db.execute(query)
        return list(result.scalars().all())
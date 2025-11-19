from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.badge import Badge
from src.repositories.base import BaseRepository


class BadgeRepository(BaseRepository[Badge]):
    """Repository for Badge model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Badge)

    async def get_by_api_key_id(self, api_key_id: int) -> Optional[Badge]:
        """Get badge by API key ID."""
        result = await self.db.execute(
            select(Badge).filter(Badge.api_key_id == api_key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_uuid(self, badge_uuid: UUID) -> Optional[Badge]:
        """Get badge by UUID."""
        result = await self.db.execute(
            select(Badge).filter(Badge.badge_uuid == badge_uuid)
        )
        return result.scalar_one_or_none()

    async def create_badge(self, api_key_id: int, badge_uuid: UUID, is_public: bool = False) -> Badge:
        """Create a new badge."""
        return await self.create({
            "api_key_id": api_key_id,
            "badge_uuid": badge_uuid,
            "is_public": is_public
        })

    async def update_visibility(self, badge_id: int, is_public: bool) -> Optional[Badge]:
        """Update badge visibility."""
        return await self.update(badge_id, {"is_public": is_public})

"""Repository for BadgeToken model operations."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.badge_token import BadgeToken
from src.repositories.base import BaseRepository


class BadgeTokenRepository(BaseRepository[BadgeToken]):
    """Repository for BadgeToken model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, BadgeToken)

    async def get_by_token(self, token: str) -> Optional[BadgeToken]:
        """Get badge token by token value."""
        result = await self.db.execute(
            select(BadgeToken).filter(BadgeToken.token == token)
        )
        return result.scalar_one_or_none()

    async def get_active_by_token(self, token: str) -> Optional[BadgeToken]:
        """Get active badge token by token value."""
        result = await self.db.execute(
            select(BadgeToken).filter(
                BadgeToken.token == token,
                BadgeToken.is_active == True  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Optional[BadgeToken]:
        """Get badge token for a user (users have at most one)."""
        result = await self.db.execute(
            select(BadgeToken).filter(BadgeToken.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user_id(self, user_id: int) -> Optional[BadgeToken]:
        """Get active badge token for a user."""
        result = await self.db.execute(
            select(BadgeToken).filter(
                BadgeToken.user_id == user_id,
                BadgeToken.is_active == True  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def create_badge_token(self, user_id: int, token: str) -> BadgeToken:
        """Create a new badge token."""
        return await self.create({
            "user_id": user_id,
            "token": token,
            "is_active": True
        })

    async def deactivate_by_user_id(self, user_id: int) -> bool:
        """Deactivate all badge tokens for a user."""
        badge_token = await self.get_by_user_id(user_id)
        if badge_token:
            await self.update(badge_token.id, {"is_active": False})
            return True
        return False

    async def update_last_used(self, token_id: int) -> Optional[BadgeToken]:
        """Update the last_used_at timestamp for a badge token."""
        return await self.update(token_id, {"last_used_at": datetime.utcnow()})

    async def token_exists(self, token: str) -> bool:
        """Check if a badge token exists."""
        result = await self.db.execute(
            select(BadgeToken.id).filter(BadgeToken.token == token)
        )
        return result.scalar_one_or_none() is not None

    async def get_all_active_tokens(self) -> List[BadgeToken]:
        """Get all active badge tokens."""
        result = await self.db.execute(
            select(BadgeToken).filter(BadgeToken.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

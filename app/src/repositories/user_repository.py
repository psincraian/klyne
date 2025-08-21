from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.db.execute(
            select(User).filter(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by verification token."""
        result = await self.db.execute(
            select(User).filter(User.verification_token == token)
        )
        return result.scalar_one_or_none()

    async def create_user(self, email: str, hashed_password: str, 
                         verification_token: str, verification_token_expires: datetime) -> User:
        """Create a new user with verification token."""
        return await self.create({
            "email": email,
            "hashed_password": hashed_password,
            "verification_token": verification_token,
            "verification_token_expires": verification_token_expires,
            "is_verified": False,
            "is_active": True,
            "is_admin": False
        })

    async def verify_user(self, user_id: int) -> Optional[User]:
        """Mark user as verified and clear verification token."""
        return await self.update(user_id, {
            "is_verified": True,
            "verification_token": None,
            "verification_token_expires": None
        })

    async def update_verification_token(self, user_id: int, token: str, 
                                       expires: datetime) -> Optional[User]:
        """Update user's verification token."""
        return await self.update(user_id, {
            "verification_token": token,
            "verification_token_expires": expires
        })

    async def update_subscription(self, user_id: int, subscription_tier: Optional[str],
                                 subscription_status: Optional[str], 
                                 subscription_updated_at: Optional[datetime]) -> Optional[User]:
        """Update user's subscription information."""
        return await self.update(user_id, {
            "subscription_tier": subscription_tier,
            "subscription_status": subscription_status,
            "subscription_updated_at": subscription_updated_at
        })

    async def get_active_users(self) -> List[User]:
        """Get all active users."""
        result = await self.db.execute(
            select(User).filter(User.is_active)
        )
        return list(result.scalars().all())

    async def get_verified_users(self) -> List[User]:
        """Get all verified users."""
        result = await self.db.execute(
            select(User).filter(User.is_verified)
        )
        return list(result.scalars().all())

    async def get_users_with_active_subscription(self) -> List[User]:
        """Get all users with active subscriptions."""
        result = await self.db.execute(
            select(User).filter(
                and_(
                    User.subscription_status == "active",
                    User.is_active,
                    User.is_verified
                )
            )
        )
        return list(result.scalars().all())

    async def get_admin_users(self) -> List[User]:
        """Get all admin users."""
        result = await self.db.execute(
            select(User).filter(User.is_admin)
        )
        return list(result.scalars().all())

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        result = await self.db.execute(
            select(User.id).filter(User.email == email)
        )
        return result.scalar_one_or_none() is not None

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user account."""
        return await self.update(user_id, {"is_active": False})

    async def activate_user(self, user_id: int) -> Optional[User]:
        """Activate a user account."""
        return await self.update(user_id, {"is_active": True})

    async def make_admin(self, user_id: int) -> Optional[User]:
        """Grant admin privileges to a user."""
        return await self.update(user_id, {"is_admin": True})

    async def remove_admin(self, user_id: int) -> Optional[User]:
        """Remove admin privileges from a user."""
        return await self.update(user_id, {"is_admin": False})
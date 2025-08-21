from typing import Optional
import logging
from fastapi import Request, HTTPException

from src.core.auth import is_authenticated, get_current_user_id
from src.models.user import User
from src.repositories.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication-related business logic."""

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def get_current_user_if_authenticated(self, request: Request) -> Optional[User]:
        """Helper function to get the current user if authenticated, None otherwise."""
        if not is_authenticated(request):
            return None

        user_id = get_current_user_id(request)
        if not user_id:
            return None

        return await self.uow.users.get_by_id(user_id)

    async def require_active_subscription(self, request: Request) -> User:
        """Require user to be authenticated and have an active subscription."""
        if not is_authenticated(request):
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = get_current_user_id(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if user.subscription_status != "active":
            raise HTTPException(status_code=403, detail="Active subscription required")

        return user

    async def get_current_user(self, request: Request) -> User:
        """Get current authenticated user or raise exception."""
        if not is_authenticated(request):
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = get_current_user_id(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    async def require_admin(self, request: Request) -> User:
        """Require user to be authenticated and have admin privileges."""
        user = await self.get_current_user(request)
        
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        return user

    async def require_verified_user(self, request: Request) -> User:
        """Require user to be authenticated and verified."""
        user = await self.get_current_user(request)
        
        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Email verification required")

        return user

    async def require_active_user(self, request: Request) -> User:
        """Require user to be authenticated and active."""
        user = await self.get_current_user(request)
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")

        return user
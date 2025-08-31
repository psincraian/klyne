from datetime import datetime, timezone
from typing import Optional, List
import logging
from fastapi import HTTPException

from src.core.auth import (
    get_password_hash, 
    verify_password, 
    generate_verification_token, 
    get_verification_token_expiry
)
from src.models.user import User
from src.repositories.unit_of_work import AbstractUnitOfWork
from src.schemas.user import UserCreate, UserLogin
from src.services.email import EmailService

logger = logging.getLogger(__name__)


class UserService:
    """Service for user-related business logic."""

    def __init__(self, uow: AbstractUnitOfWork, email_service: Optional[EmailService] = None):
        self.uow = uow
        self.email_service = email_service

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user with email verification."""
        # Check if user already exists
        existing_user = await self.uow.users.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Generate verification token
        verification_token = generate_verification_token()
        verification_expires = get_verification_token_expiry()

        # Create user
        user = await self.uow.users.create_user(
            email=user_data.email,
            hashed_password=hashed_password,
            verification_token=verification_token,
            verification_token_expires=verification_expires
        )

        # Send verification email if email service is available
        if self.email_service:
            try:
                await self.email_service.send_verification_email(
                    user.email, verification_token, user.id
                )
            except Exception as e:
                logger.error(f"Failed to send verification email to {user.email}: {e}")
                # Don't fail registration if email sending fails

        await self.uow.commit()
        logger.info(f"User registered successfully: {user.email}")
        return user

    async def authenticate_user(self, login_data: UserLogin) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.uow.users.get_by_email(login_data.email)
        if not user:
            return None

        if not verify_password(login_data.password, user.hashed_password):
            return None

        if not user.is_active:
            raise HTTPException(status_code=400, detail="User account is deactivated")

        return user

    async def verify_user_email(self, verification_token: str) -> User:
        """Verify user email with verification token."""
        user = await self.uow.users.get_by_verification_token(verification_token)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification token")

        if user.verification_token_expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Verification token has expired")

        if user.is_verified:
            raise HTTPException(status_code=400, detail="User is already verified")

        # Verify the user
        verified_user = await self.uow.users.verify_user(user.id)
        await self.uow.commit()
        
        logger.info(f"User email verified successfully: {user.email}")
        return verified_user

    async def resend_verification_email(self, email: str) -> bool:
        """Resend verification email to user."""
        user = await self.uow.users.get_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_verified:
            raise HTTPException(status_code=400, detail="User is already verified")

        # Generate new verification token
        verification_token = generate_verification_token()
        verification_expires = get_verification_token_expiry()

        # Update user with new token
        await self.uow.users.update_verification_token(
            user.id, verification_token, verification_expires
        )

        # Send verification email
        if self.email_service:
            try:
                await self.email_service.send_verification_email(
                    user.email, verification_token, user.id
                )
                await self.uow.commit()
                logger.info(f"Verification email resent to: {user.email}")
                return True
            except Exception as e:
                logger.error(f"Failed to resend verification email to {user.email}: {e}")
                await self.uow.rollback()
                raise HTTPException(status_code=500, detail="Failed to send verification email")
        else:
            await self.uow.commit()
            logger.warning("Email service not available, but token updated")
            return True

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.uow.users.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.uow.users.get_by_email(email)

    async def update_user_subscription(self, user_id: int, subscription_tier: Optional[str],
                                     subscription_status: Optional[str]) -> User:
        """Update user's subscription information."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        updated_user = await self.uow.users.update_subscription(
            user_id=user_id,
            subscription_tier=subscription_tier,
            subscription_status=subscription_status,
            subscription_updated_at=datetime.now(timezone.utc)
        )
        
        await self.uow.commit()
        logger.info(f"Updated subscription for user {user.email}: {subscription_tier} - {subscription_status}")
        return updated_user

    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate a user account."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        deactivated_user = await self.uow.users.deactivate_user(user_id)
        await self.uow.commit()
        
        logger.info(f"User deactivated: {user.email}")
        return deactivated_user

    async def activate_user(self, user_id: int) -> User:
        """Activate a user account."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        activated_user = await self.uow.users.activate_user(user_id)
        await self.uow.commit()
        
        logger.info(f"User activated: {user.email}")
        return activated_user

    async def get_users_with_active_subscription(self) -> List[User]:
        """Get all users with active subscriptions."""
        return await self.uow.users.get_users_with_active_subscription()

    async def user_has_active_subscription(self, user_id: int) -> bool:
        """Check if user has an active subscription."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            return False
            
        return (user.subscription_status == "active" and 
                user.is_active and 
                user.is_verified)

    async def make_admin(self, user_id: int) -> User:
        """Grant admin privileges to a user."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        admin_user = await self.uow.users.make_admin(user_id)
        await self.uow.commit()
        
        logger.info(f"User granted admin privileges: {user.email}")
        return admin_user

    async def remove_admin(self, user_id: int) -> User:
        """Remove admin privileges from a user."""
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        regular_user = await self.uow.users.remove_admin(user_id)
        await self.uow.commit()
        
        logger.info(f"Admin privileges removed from user: {user.email}")
        return regular_user

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin."""
        user = await self.uow.users.get_by_id(user_id)
        return user.is_admin if user else False
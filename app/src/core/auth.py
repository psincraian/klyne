from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import logging
from passlib.context import CryptContext
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from src.models.user import User

# Configure logging for auth module
logger = logging.getLogger(__name__)

# Suppress passlib bcrypt version warnings
logging.getLogger("passlib").setLevel(logging.ERROR)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

VERIFICATION_TOKEN_EXPIRE_HOURS = 24


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Failed to hash password: {str(e)}")
        raise HTTPException(status_code=500, detail="Password hashing failed")


def create_session(request: Request, user_id: int, user_email: str) -> None:
    """Create a user session."""
    request.session["user_id"] = user_id
    request.session["user_email"] = user_email


def get_current_user_id(request: Request) -> Optional[int]:
    """Get current user ID from session."""
    return request.session.get("user_id")


def get_current_user_email(request: Request) -> Optional[str]:
    """Get current user email from session."""
    return request.session.get("user_email")


def logout_user(request: Request) -> None:
    """Clear user session."""
    request.session.clear()


def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated."""
    return "user_id" in request.session


def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(32)


def get_verification_token_expiry() -> datetime:
    """Get expiry time for verification token."""
    return datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)


async def require_authentication(request: Request) -> int:
    """Dependency to require authentication and return user ID."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)) -> int:
    """Dependency to require admin authentication and return user ID."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Check if user is admin
    from sqlalchemy import select

    result = await db.execute(select(User.is_admin).where(User.id == user_id))
    is_admin = result.scalar_one_or_none()

    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return user_id

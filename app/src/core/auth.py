from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
from passlib.context import CryptContext
from fastapi import Request
from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

VERIFICATION_TOKEN_EXPIRE_HOURS = 24


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


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
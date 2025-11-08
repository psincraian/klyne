from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.api_key import APIKey
from src.models.user import User


async def requires_active_subscription_for_api_key(
    api_key: APIKey, db: AsyncSession = Depends(get_db)
) -> User:
    """Require API key to be valid and associated with an active subscription (including free plan)."""
    user = await db.execute(select(User).filter(User.id == api_key.user_id))
    user = user.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.has_active_subscription:
        raise HTTPException(status_code=403, detail="Active subscription required")

    return user


async def requires_active_subscription(user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    """Require user to have an active subscription."""
    user = await db.execute(select(User).filter(User.id == user_id))
    user = user.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email verification required")

    if not user.has_active_subscription:
        raise HTTPException(
            status_code=403, 
            detail="An active subscription is required to access this feature. Please subscribe to get started."
        )

    return user


def get_subscription_error_context(user: User | None = None) -> dict:
    """Get context for subscription error pages."""
    if not user:
        return {
            "title": "Access Denied",
            "message": "Please log in to access this feature.",
            "cta_text": "Log In",
            "cta_url": "/login"
        }
    
    if not user.is_verified:
        return {
            "title": "Email Verification Required",
            "message": "Please verify your email address to continue.",
            "cta_text": "Resend Verification",
            "cta_url": "/resend-verification"
        }
    
    if user.subscription_tier and user.subscription_status != "active":
        return {
            "title": "Subscription Expired",
            "message": "Your subscription has expired. Reactivate to continue using Klyne analytics.",
            "cta_text": "Reactivate Subscription",
            "cta_url": "/pricing"
        }
    else:
        return {
            "title": "Subscription Required",
            "message": "Get started with package analytics by choosing a subscription plan that fits your needs.",
            "cta_text": "View Pricing Plans",
            "cta_url": "/pricing"
        }
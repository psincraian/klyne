"""
Utilities for subscription and package limit validation.
"""

from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.user import User
from src.models.api_key import APIKey


async def get_package_limit_for_tier(subscription_tier: str, subscription_status: str = None) -> int:
    """Get the package limit for a given subscription tier."""
    if subscription_tier == "free" and subscription_status == "active":
        return 1
    elif subscription_tier == "starter" and subscription_status == "active":
        return 1
    elif subscription_tier in ["pro", "enterprise"] and subscription_status == "active":
        return -1  # Unlimited
    else:
        # No subscription or inactive subscription - no access
        return 0


async def can_user_create_package(db: AsyncSession, user_id: int) -> Tuple[bool, str, int, int]:
    """
    Check if a user can create a new package based on their subscription tier.
    
    Returns:
        Tuple of (can_create: bool, error_message: str, current_count: int, limit: int)
    """
    # Get user and their subscription tier
    user_result = await db.execute(select(User).filter(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "User not found", 0, 0
    
    # Get current package count
    package_count_result = await db.execute(
        select(func.count(APIKey.id)).filter(APIKey.user_id == user_id)
    )
    current_count = package_count_result.scalar() or 0
    
    # Check subscription status
    if not user.subscription_tier or user.subscription_status != "active":
        error_msg = "An active subscription is required to create API keys and track package analytics. Please subscribe to get started."
        return False, error_msg, current_count, 0
    
    # Get limit for user's active tier
    limit = await get_package_limit_for_tier(user.subscription_tier, user.subscription_status)
    
    # Check if user can create more packages
    if limit == -1:  # Unlimited
        return True, "", current_count, limit
    elif current_count < limit:
        return True, "", current_count, limit
    else:
        error_msg = f"You've reached the limit of {limit} package{'s' if limit != 1 else ''} for your {user.subscription_tier.title()} plan. Please upgrade to Pro to add more packages."
        return False, error_msg, current_count, limit


async def get_user_package_usage(db: AsyncSession, user_id: int) -> Tuple[int, int]:
    """
    Get current package usage and limit for a user.
    
    Returns:
        Tuple of (current_count: int, limit: int)
    """
    # Get user and their subscription tier
    user_result = await db.execute(select(User).filter(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        return 0, 0
    
    # Get current package count
    package_count_result = await db.execute(
        select(func.count(APIKey.id)).filter(APIKey.user_id == user_id)
    )
    current_count = package_count_result.scalar() or 0
    
    # Get limit for user's tier (considering subscription status)
    if user.subscription_tier and user.subscription_status == "active":
        limit = await get_package_limit_for_tier(user.subscription_tier, user.subscription_status)
    else:
        limit = 0  # No access without active subscription
    
    return current_count, limit
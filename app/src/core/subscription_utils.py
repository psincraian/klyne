"""
Utilities for subscription and package limit validation.
"""

from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.user import User
from src.models.api_key import APIKey


async def get_package_limit_for_tier(subscription_tier: str) -> int:
    """Get the package limit for a given subscription tier."""
    if subscription_tier == "starter":
        return 1
    elif subscription_tier in ["pro", "enterprise"]:
        return -1  # Unlimited
    else:
        # No subscription - treat as starter for now
        return 1


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
    
    # Get limit for user's tier
    tier = user.subscription_tier or "starter"  # Default to starter if no subscription
    limit = await get_package_limit_for_tier(tier)
    
    # Check if user can create more packages
    if limit == -1:  # Unlimited
        return True, "", current_count, limit
    elif current_count < limit:
        return True, "", current_count, limit
    else:
        error_msg = f"You've reached the limit of {limit} package{'s' if limit != 1 else ''} for your {tier.title()} plan. Please upgrade to Pro to add more packages."
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
    
    # Get limit for user's tier
    tier = user.subscription_tier or "starter"
    limit = await get_package_limit_for_tier(tier)
    
    return current_count, limit
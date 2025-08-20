from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.api_key import APIKey
from src.models.user import User


async def requires_active_subscription_for_api_key(
    api_key: APIKey, db: AsyncSession = Depends(get_db)
) -> User:
    """Require API key to be valid and associated with an active subscription."""
    user = await db.execute(select(User).filter(User.id == api_key.user_id))
    user = user.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.subscription_status is None or user.subscription_status != "active":
        raise HTTPException(status_code=403, detail="Active subscription required")

    return user
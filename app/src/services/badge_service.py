"""Service for badge token management and badge generation."""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.badge_token import BadgeToken
from src.models.user import User
from src.repositories.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


class BadgeService:
    """Service for managing badge tokens and generating badges."""

    @staticmethod
    async def generate_badge_token(user_id: int, uow: AbstractUnitOfWork) -> BadgeToken:
        """
        Generate a new badge token for a user.
        If user already has a token, deactivate it and create a new one.
        """
        logger.info(f"Generating badge token for user {user_id}")

        # Check if user already has a badge token
        existing_token = await uow.badge_tokens.get_by_user_id(user_id)

        if existing_token:
            logger.info(f"User {user_id} already has a badge token, deactivating old token")
            await uow.badge_tokens.deactivate_by_user_id(user_id)

        # Generate new token
        token = BadgeToken.generate_token()

        # Create new badge token
        badge_token = await uow.badge_tokens.create_badge_token(user_id, token)
        await uow.commit()

        logger.info(f"Created new badge token {badge_token.id} for user {user_id}")
        return badge_token

    @staticmethod
    async def get_user_badge_token(user_id: int, uow: AbstractUnitOfWork) -> Optional[BadgeToken]:
        """Get the active badge token for a user."""
        logger.debug(f"Fetching badge token for user {user_id}")
        return await uow.badge_tokens.get_active_by_user_id(user_id)

    @staticmethod
    async def revoke_badge_token(user_id: int, uow: AbstractUnitOfWork) -> bool:
        """Revoke (deactivate) a user's badge token."""
        logger.info(f"Revoking badge token for user {user_id}")
        success = await uow.badge_tokens.deactivate_by_user_id(user_id)

        if success:
            await uow.commit()
            logger.info(f"Successfully revoked badge token for user {user_id}")
        else:
            logger.warning(f"No badge token found to revoke for user {user_id}")

        return success

    @staticmethod
    async def get_badge_token_by_token(token: str, uow: AbstractUnitOfWork) -> Optional[BadgeToken]:
        """Get an active badge token by its token value."""
        logger.debug("Fetching badge token by token value")
        badge_token = await uow.badge_tokens.get_active_by_token(token)

        if badge_token:
            # Update last_used_at
            await uow.badge_tokens.update_last_used(badge_token.id)
            await uow.commit()

        return badge_token

    @staticmethod
    async def get_total_user_count(db: AsyncSession) -> int:
        """Get the total count of verified and active users."""
        logger.debug("Fetching total user count")
        result = await db.execute(
            select(func.count(User.id)).filter(
                User.is_verified == True,  # noqa: E712
                User.is_active == True  # noqa: E712
            )
        )
        count = result.scalar()
        logger.debug(f"Total user count: {count}")
        return count

    @staticmethod
    def generate_badge_svg(count: int) -> str:
        """
        Generate an SVG badge showing the user count.
        Similar to shields.io style badges.
        """
        # Format the count with commas for readability
        count_str = f"{count:,}"

        # Calculate width based on text length (approximate)
        label = "users"
        label_width = 45
        count_width = max(40, len(count_str) * 8 + 20)
        total_width = label_width + count_width

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_width}" height="20" role="img" aria-label="{label}: {count_str}">
    <title>{label}: {count_str}</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="{label_width}" height="20" fill="#555"/>
        <rect x="{label_width}" width="{count_width}" height="20" fill="#4c1"/>
        <rect width="{total_width}" height="20" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="{label_width * 10 // 2}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(label_width - 10) * 10}">{label}</text>
        <text x="{label_width * 10 // 2}" y="140" transform="scale(.1)" fill="#fff" textLength="{(label_width - 10) * 10}">{label}</text>
        <text aria-hidden="true" x="{(label_width + count_width // 2) * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(count_width - 10) * 10}">{count_str}</text>
        <text x="{(label_width + count_width // 2) * 10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(count_width - 10) * 10}">{count_str}</text>
    </g>
</svg>'''
        return svg

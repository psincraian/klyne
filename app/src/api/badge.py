"""API endpoints for badge token management and badge display."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import require_authentication
from src.core.database import get_db
from src.repositories.unit_of_work import get_unit_of_work, AbstractUnitOfWork
from src.schemas.badge import BadgeTokenResponse, BadgeURLResponse
from src.services.badge_service import BadgeService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/badge-token", response_model=BadgeURLResponse)
async def generate_badge_token(
    request: Request,
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
    user_id: int = Depends(require_authentication),
):
    """
    Generate a new badge token for the authenticated user.
    If a token already exists, it will be deactivated and a new one created.
    """
    logger.info(f"User {user_id} requesting badge token generation")

    try:
        badge_token = await BadgeService.generate_badge_token(user_id, uow)

        # Construct the badge URL
        base_url = str(request.base_url).rstrip("/")
        badge_url = f"{base_url}/badge/{badge_token.token}"

        # Generate markdown and HTML snippets
        markdown = f"![Klyne Users]({badge_url})"
        html = f'<img src="{badge_url}" alt="Klyne Users">'

        return BadgeURLResponse(
            token=badge_token.token,
            badge_url=badge_url,
            markdown=markdown,
            html=html,
        )
    except Exception as e:
        logger.error(f"Error generating badge token for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate badge token")


@router.get("/api/badge-token", response_model=BadgeTokenResponse)
async def get_badge_token(
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
    user_id: int = Depends(require_authentication),
):
    """Get the current active badge token for the authenticated user."""
    logger.debug(f"User {user_id} requesting their badge token")

    badge_token = await BadgeService.get_user_badge_token(user_id, uow)

    if not badge_token:
        raise HTTPException(
            status_code=404, detail="No active badge token found. Please generate one first."
        )

    return badge_token


@router.delete("/api/badge-token")
async def revoke_badge_token(
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
    user_id: int = Depends(require_authentication),
):
    """Revoke (deactivate) the authenticated user's badge token."""
    logger.info(f"User {user_id} requesting to revoke their badge token")

    success = await BadgeService.revoke_badge_token(user_id, uow)

    if not success:
        raise HTTPException(status_code=404, detail="No badge token found to revoke")

    return {"message": "Badge token revoked successfully"}


@router.get("/badge/{token}")
async def get_badge_svg(
    token: str,
    db: AsyncSession = Depends(get_db),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work),
):
    """
    Public endpoint that returns an SVG badge showing the total user count.
    This endpoint is accessible without authentication but requires a valid token.
    """
    logger.debug("Badge request received for token")

    # Verify the token is valid and active
    badge_token = await BadgeService.get_badge_token_by_token(token, uow)

    if not badge_token:
        logger.warning("Invalid or inactive badge token used")
        raise HTTPException(status_code=404, detail="Invalid badge token")

    # Get the total user count
    total_users = await BadgeService.get_total_user_count(db)

    # Generate the SVG badge
    svg_content = BadgeService.generate_badge_svg(total_users)

    # Return SVG with proper content type and caching headers
    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

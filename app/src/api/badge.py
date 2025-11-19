import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from src.core.auth import get_current_user_id
from src.core.service_dependencies import get_api_key_service
from src.schemas.api_key import BadgeResponse, APIKeyUpdate
from src.services.api_key_service import APIKeyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/badge", tags=["badge"])


def generate_badge_svg(package_name: str, unique_users: int) -> str:
    """Generate SVG badge for unique users count."""
    # Calculate text widths (approximate)
    label = "unique users"
    value = str(unique_users)

    # Approximate character width in pixels
    char_width = 6.5
    label_width = len(label) * char_width + 10
    value_width = len(value) * char_width + 10
    total_width = label_width + value_width

    # SVG template
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{int(total_width)}" height="20" role="img" aria-label="{label}: {value}">
    <title>{label}: {value}</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="{int(total_width)}" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="{int(label_width)}" height="20" fill="#555"/>
        <rect x="{int(label_width)}" width="{int(value_width)}" height="20" fill="#4c1"/>
        <rect width="{int(total_width)}" height="20" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="{int(label_width/2*10)}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{int((len(label) * char_width)*10)}">{label}</text>
        <text x="{int(label_width/2*10)}" y="140" transform="scale(.1)" fill="#fff" textLength="{int((len(label) * char_width)*10)}">{label}</text>
        <text aria-hidden="true" x="{int((label_width + value_width/2)*10)}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{int((len(value) * char_width)*10)}">{value}</text>
        <text x="{int((label_width + value_width/2)*10)}" y="140" transform="scale(.1)" fill="#fff" textLength="{int((len(value) * char_width)*10)}">{value}</text>
    </g>
</svg>'''

    return svg


@router.get("/{badge_uuid}.svg", response_class=Response)
async def get_badge_svg(
    badge_uuid: str,
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Get badge SVG for a specific badge UUID.
    This is a public endpoint that only works if the badge is marked as public.

    Usage:
    - Embed in README: ![Users](https://klyne.app/badge/{badge_uuid}.svg)
    """
    logger.debug(f"Badge request for UUID {badge_uuid}")

    # Get badge data (returns None if not public or invalid UUID)
    badge_data = await api_key_service.get_badge_data_by_uuid(badge_uuid)

    if not badge_data:
        logger.debug(f"Badge not found or not public for UUID {badge_uuid}")
        # Return a "badge not public" SVG instead of 404
        svg = generate_badge_svg("unique users", 0)
        return Response(content=svg, media_type="image/svg+xml")

    # Generate and return SVG
    svg = generate_badge_svg(badge_data["package_name"], badge_data["unique_users"])

    # Add cache headers (cache for 1 hour)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Type": "image/svg+xml; charset=utf-8"
        }
    )


@router.get("/{badge_uuid}/data")
async def get_badge_data(
    badge_uuid: str,
    api_key_service: APIKeyService = Depends(get_api_key_service)
) -> BadgeResponse:
    """
    Get badge data as JSON for a specific badge UUID.
    This is a public endpoint that only works if the badge is marked as public.
    """
    logger.debug(f"Badge data request for UUID {badge_uuid}")

    badge_data = await api_key_service.get_badge_data_by_uuid(badge_uuid)

    if not badge_data:
        raise HTTPException(status_code=404, detail="Badge not found or not public")

    return BadgeResponse(**badge_data)


@router.patch("/{api_key_id}/visibility")
async def update_badge_visibility(
    request: Request,
    api_key_id: int,
    update: APIKeyUpdate,
    api_key_service: APIKeyService = Depends(get_api_key_service)
):
    """
    Update badge visibility for an API key.
    Requires authentication and ownership of the API key.
    """
    # Check if user is authenticated
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Update badge visibility
    if update.badge_public is None:
        raise HTTPException(status_code=400, detail="badge_public field is required")

    updated_key = await api_key_service.update_badge_visibility(
        user_id, api_key_id, update.badge_public
    )

    logger.info(f"Updated badge visibility for API key {api_key_id} to {update.badge_public}")

    return {
        "success": True,
        "api_key_id": api_key_id,
        "badge_public": updated_key.badge_public
    }

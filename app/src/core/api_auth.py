from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from src.core.database import get_db
from src.models.api_key import APIKey

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_api_key_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """
    Validate API key from Authorization header and return the APIKey object.

    Expects header: Authorization: Bearer klyne_abc123...
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="API key required. Include 'Authorization: Bearer <api_key>' header.",
        )

    api_key_value = credentials.credentials

    if not api_key_value:
        raise HTTPException(status_code=401, detail="Invalid API key format")

    # Validate API key format
    if not api_key_value.startswith("klyne_"):
        raise HTTPException(
            status_code=401, detail="Invalid API key format. Must start with 'klyne_'"
        )

    # Look up API key in database
    try:
        result = await db.execute(select(APIKey).filter(APIKey.key == api_key_value))
        api_key = result.scalar_one_or_none()

        if not api_key:
            logger.warning(f"Invalid API key attempted: {api_key_value[:20]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")

        logger.info(f"API key validated for package: {api_key.package_name}")
        return api_key

    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        raise HTTPException(status_code=500, detail="Error validating API key")


async def validate_package_match(api_key: APIKey, package_name: str) -> None:
    """
    Validate that the API key matches the package name in the request.
    """
    if api_key.package_name != package_name:
        logger.warning(
            f"Package name mismatch. API key for '{api_key.package_name}' "
            f"used for package '{package_name}'"
        )
        raise HTTPException(
            status_code=403,
            detail=f"API key is not authorized for package '{package_name}'. "
            f"This key is for package '{api_key.package_name}'",
        )


# Convenience dependency that combines auth and package validation
async def authenticate_analytics_request(
    api_key: APIKey = Depends(get_api_key_from_token),
) -> APIKey:
    """
    Authenticate analytics API requests.
    Package validation happens in the endpoint after parsing the request body.
    """
    return api_key

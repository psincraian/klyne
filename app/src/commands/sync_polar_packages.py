"""
Command to sync package counts for all users to Polar.
This is run as a scheduled task to ensure Polar has up-to-date package usage data.
"""

import logging
from datetime import datetime, timezone
from typing import List, Tuple, TypedDict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal
from src.models.user import User
from src.models.api_key import APIKey
from src.services.polar import polar_service

logger = logging.getLogger(__name__)


class SyncResult(TypedDict):
    """Result structure for sync task execution."""
    start_time: str
    total_users: int
    successful_syncs: int
    failed_syncs: int
    errors: list[str]
    end_time: str
    duration_seconds: float


async def sync_all_users_packages() -> SyncResult:
    """
    Sync package counts for all users to Polar.

    Returns:
        Dict with sync results including success/failure counts and any errors
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Starting daily Polar package sync...")

    results: SyncResult = {
        "start_time": start_time.isoformat(),
        "total_users": 0,
        "successful_syncs": 0,
        "failed_syncs": 0,
        "errors": [],
        "end_time": "",
        "duration_seconds": 0.0
    }
    
    try:
        async with AsyncSessionLocal() as db:
            # Get all users with their API key counts in a single query
            user_package_counts = await _get_user_package_counts(db)
            results["total_users"] = len(user_package_counts)
            
            logger.info(f"Found {results['total_users']} users to sync")
            
            # Sync each user's package count
            for user_id, package_count in user_package_counts:
                try:
                    success = await polar_service.ingest_event(
                        event_name="packages",
                        external_customer_id=str(user_id),
                        metadata={"packagesCount": package_count}
                    )
                    
                    if success:
                        results["successful_syncs"] += 1
                        logger.debug(f"Successfully synced user {user_id} with {package_count} packages")
                    else:
                        results["failed_syncs"] += 1
                        error_msg = f"Failed to sync user {user_id} (no exception thrown)"
                        results["errors"].append(error_msg)
                        logger.warning(error_msg)
                        
                except Exception as e:
                    results["failed_syncs"] += 1
                    error_msg = f"Exception syncing user {user_id}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
    
    except Exception as e:
        error_msg = f"Critical error during sync: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(error_msg, exc_info=True)
    
    finally:
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        results["end_time"] = end_time.isoformat()
        results["duration_seconds"] = duration
        
        logger.info(
            f"Polar package sync completed in {duration:.2f}s. "
            f"Success: {results['successful_syncs']}, "
            f"Failed: {results['failed_syncs']}, "
            f"Total: {results['total_users']}"
        )
        
        if results["errors"]:
            logger.warning(f"Encountered {len(results['errors'])} errors during sync")
    
    return results


async def _get_user_package_counts(db: AsyncSession) -> List[Tuple[int, int]]:
    """
    Get all users and their API key counts in an efficient single query.
    
    Args:
        db: Database session
        
    Returns:
        List of tuples (user_id, package_count)
    """
    query = (
        select(
            User.id.label("user_id"),
            func.count(APIKey.id).label("package_count")
        )
        .outerjoin(APIKey, User.id == APIKey.user_id)
        .where(User.is_active)  # Only sync active users
        .group_by(User.id)
        .order_by(User.id)
    )
    
    result = await db.execute(query)
    return [(row.user_id, row.package_count) for row in result.all()]


async def sync_single_user_packages(user_id: int) -> bool:
    """
    Sync package count for a single user to Polar.
    Useful for testing or manual sync of specific users.
    
    Args:
        user_id: ID of the user to sync
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Syncing packages for user {user_id}")
    
    try:
        async with AsyncSessionLocal() as db:
            # Get package count for this user
            query = (
                select(func.count(APIKey.id))
                .where(APIKey.user_id == user_id)
            )
            result = await db.execute(query)
            package_count = result.scalar() or 0
            
            logger.info(f"User {user_id} has {package_count} packages")
            
            # Send to Polar
            success = await polar_service.ingest_event(
                event_name="packages",
                external_customer_id=str(user_id),
                metadata={"packagesCount": package_count}
            )
            
            if success:
                logger.info(f"Successfully synced user {user_id}")
            else:
                logger.error(f"Failed to sync user {user_id}")
                
            return success
            
    except Exception as e:
        logger.error(f"Exception syncing user {user_id}: {e}", exc_info=True)
        return False
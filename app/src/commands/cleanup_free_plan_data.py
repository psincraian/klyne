"""
Command to clean up old analytics data for free plan users.
This job runs daily and removes analytics events older than the retention period
for users on the free plan.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from sqlalchemy import select, delete, text

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.models.analytics_event import AnalyticsEvent
from src.models.api_key import APIKey
from src.models.user import User

logger = logging.getLogger(__name__)


async def cleanup_free_plan_analytics_data(db=None) -> Dict[str, Any]:
    """
    Clean up old analytics data for free plan users.

    Removes analytics events older than FREE_PLAN_DATA_RETENTION_DAYS
    for users on the free plan.

    Args:
        db: Optional database session. If not provided, creates a new one.

    Returns:
        Dictionary with cleanup statistics
    """
    logger.info(f"Starting free plan data cleanup (retention: {settings.FREE_PLAN_DATA_RETENTION_DAYS} days)")

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.FREE_PLAN_DATA_RETENTION_DAYS)
    total_deleted = 0
    users_affected = 0
    errors = []

    async def _cleanup(session):
        nonlocal total_deleted, users_affected, errors
        try:
            # Get all API keys for free plan users
            free_plan_api_keys_query = select(APIKey.key).join(User).where(
                User.subscription_tier == 'free'
            )
            free_plan_api_keys_result = await session.execute(free_plan_api_keys_query)
            free_plan_api_keys = [row.key for row in free_plan_api_keys_result.fetchall()]

            if not free_plan_api_keys:
                logger.info("No free plan users found, skipping cleanup")
                return {
                    "success": True,
                    "total_deleted": 0,
                    "users_affected": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                    "errors": []
                }

            logger.info(f"Found {len(free_plan_api_keys)} free plan API keys to clean up")

            # Delete old analytics events for free plan users
            delete_query = delete(AnalyticsEvent).where(
                AnalyticsEvent.api_key.in_(free_plan_api_keys),
                AnalyticsEvent.event_timestamp < cutoff_date
            )

            result = await session.execute(delete_query)
            total_deleted = result.rowcount
            users_affected = len(free_plan_api_keys)

            await session.commit()

            logger.info(f"Cleanup completed: deleted {total_deleted} events from {users_affected} free plan users")

            return {
                "success": True,
                "total_deleted": total_deleted,
                "users_affected": users_affected,
                "cutoff_date": cutoff_date.isoformat(),
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error during free plan data cleanup: {e}")
            errors.append(str(e))

            return {
                "success": False,
                "total_deleted": total_deleted,
                "users_affected": users_affected,
                "cutoff_date": cutoff_date.isoformat(),
                "errors": errors
            }

    # If session is provided, use it; otherwise create a new one
    if db is not None:
        return await _cleanup(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _cleanup(session)


async def get_free_plan_data_stats(db=None) -> Dict[str, Any]:
    """
    Get statistics about analytics data for free plan users.

    Args:
        db: Optional database session. If not provided, creates a new one.

    Returns:
        Dictionary with data statistics
    """
    async def _get_stats(session):
        try:
            # Count events by age for free plan users
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.FREE_PLAN_DATA_RETENTION_DAYS)

            # Get total events for free plan users
            total_events_query = text("""
                SELECT COUNT(*) as total_events
                FROM analytics_events ae
                JOIN api_keys ak ON ae.api_key = ak.key
                JOIN users u ON ak.user_id = u.id
                WHERE u.subscription_tier = 'free'
            """)

            # Get old events that would be deleted
            old_events_query = text("""
                SELECT COUNT(*) as old_events
                FROM analytics_events ae
                JOIN api_keys ak ON ae.api_key = ak.key
                JOIN users u ON ak.user_id = u.id
                WHERE u.subscription_tier = 'free'
                AND ae.event_timestamp < :cutoff_date
            """)

            total_result = await session.execute(total_events_query)
            old_result = await session.execute(old_events_query, {"cutoff_date": cutoff_date})

            total_events = total_result.fetchone().total_events
            old_events = old_result.fetchone().old_events

            return {
                "total_events": total_events,
                "old_events": old_events,
                "retention_cutoff": cutoff_date.isoformat(),
                "retention_days": settings.FREE_PLAN_DATA_RETENTION_DAYS
            }

        except Exception as e:
            logger.error(f"Error getting free plan data stats: {e}")
            return {
                "error": str(e)
            }

    # If session is provided, use it; otherwise create a new one
    if db is not None:
        return await _get_stats(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _get_stats(session)
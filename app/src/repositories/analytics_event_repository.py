from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analytics_event import AnalyticsEvent
from src.repositories.base import BaseRepository

# Whitelist of allowed dimension fields for security
ALLOWED_DIMENSION_FIELDS = {
    'os_type',
    'python_version',
    'architecture',
    'os_release',
    'python_implementation',
    'virtual_env_type',
    'installation_method'
}


class AnalyticsEventRepository(BaseRepository[AnalyticsEvent]):
    """Repository for AnalyticsEvent model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, AnalyticsEvent)

    async def get_by_api_key(self, api_key: str, limit: Optional[int] = None) -> List[AnalyticsEvent]:
        """Get events by API key."""
        query = select(AnalyticsEvent).filter(AnalyticsEvent.api_key == api_key)
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_stats_for_api_key(self, api_key: str, start_date: datetime, 
                                   end_date: datetime) -> Dict[str, Any]:
        """Get aggregated stats for an API key within date range."""
        stats_query = select(
            func.count(AnalyticsEvent.id).label("total_events"),
            func.count(func.distinct(AnalyticsEvent.session_id)).label("total_sessions"),
            func.count(func.distinct(func.date(AnalyticsEvent.event_timestamp))).label("active_days"),
        ).filter(
            and_(
                AnalyticsEvent.api_key == api_key,
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp <= end_date,
            )
        )

        result = await self.db.execute(stats_query)
        stats = result.first()

        return {
            "total_events": int(stats.total_events or 0),
            "total_sessions": int(stats.total_sessions or 0),
            "active_days": int(stats.active_days or 0)
        }

    async def get_python_version_distribution(self, api_keys: List[str], 
                                            start_date: datetime, 
                                            end_date: datetime) -> List[Dict[str, Any]]:
        """Get Python version distribution for given API keys."""
        python_stats_query = (
            select(
                AnalyticsEvent.python_version,
                func.count(AnalyticsEvent.id).label("total_events"),
                func.count(func.distinct(AnalyticsEvent.session_id)).label("total_sessions"),
            )
            .filter(
                and_(
                    AnalyticsEvent.api_key.in_(api_keys),
                    AnalyticsEvent.event_timestamp >= start_date,
                    AnalyticsEvent.event_timestamp <= end_date,
                )
            )
            .group_by(AnalyticsEvent.python_version)
            .order_by(desc("total_events"))
        )

        result = await self.db.execute(python_stats_query)
        return [
            {
                "python_version": row.python_version,
                "total_events": row.total_events,
                "total_sessions": row.total_sessions
            }
            for row in result.all()
        ]

    async def get_os_distribution(self, api_keys: List[str], 
                                 start_date: datetime, 
                                 end_date: datetime) -> List[Dict[str, Any]]:
        """Get OS distribution for given API keys."""
        os_stats_query = (
            select(
                AnalyticsEvent.os_type,
                func.count(AnalyticsEvent.id).label("total_events"),
                func.count(func.distinct(AnalyticsEvent.session_id)).label("total_sessions"),
            )
            .filter(
                and_(
                    AnalyticsEvent.api_key.in_(api_keys),
                    AnalyticsEvent.event_timestamp >= start_date,
                    AnalyticsEvent.event_timestamp <= end_date,
                )
            )
            .group_by(AnalyticsEvent.os_type)
            .order_by(desc("total_events"))
        )

        result = await self.db.execute(os_stats_query)
        return [
            {
                "os_type": row.os_type,
                "total_events": row.total_events,
                "total_sessions": row.total_sessions
            }
            for row in result.all()
        ]

    async def get_package_version_distribution(self, api_key: str, 
                                             start_date: datetime, 
                                             end_date: datetime) -> List[Dict[str, Any]]:
        """Get package version distribution for a specific API key."""
        version_stats_query = (
            select(
                AnalyticsEvent.package_version,
                func.count(AnalyticsEvent.id).label("total_events"),
                func.count(func.distinct(AnalyticsEvent.session_id)).label("total_sessions"),
            )
            .filter(
                and_(
                    AnalyticsEvent.api_key == api_key,
                    AnalyticsEvent.event_timestamp >= start_date,
                    AnalyticsEvent.event_timestamp <= end_date,
                )
            )
            .group_by(AnalyticsEvent.package_version)
            .order_by(desc("total_events"))
        )

        result = await self.db.execute(version_stats_query)
        return [
            {
                "package_version": row.package_version,
                "total_events": row.total_events,
                "total_sessions": row.total_sessions
            }
            for row in result.all()
        ]

    async def get_daily_timeseries(self, api_keys: List[str], 
                                  start_date: datetime, 
                                  end_date: datetime) -> List[Dict[str, Any]]:
        """Get daily time series data for given API keys."""
        daily_stats_query = (
            select(
                func.date(AnalyticsEvent.event_timestamp).label("date"),
                AnalyticsEvent.package_name,
                func.count(AnalyticsEvent.id).label("total_events"),
                func.count(func.distinct(AnalyticsEvent.session_id)).label("total_sessions"),
            )
            .filter(
                and_(
                    AnalyticsEvent.api_key.in_(api_keys),
                    AnalyticsEvent.event_timestamp >= start_date,
                    AnalyticsEvent.event_timestamp <= end_date,
                )
            )
            .group_by(
                func.date(AnalyticsEvent.event_timestamp), 
                AnalyticsEvent.package_name
            )
            .order_by(func.date(AnalyticsEvent.event_timestamp))
        )

        result = await self.db.execute(daily_stats_query)
        return [
            {
                "date": row.date,
                "package_name": row.package_name,
                "total_events": row.total_events,
                "total_sessions": row.total_sessions
            }
            for row in result.all()
        ]

    async def get_total_events_count(self, api_keys: List[str]) -> int:
        """Get total events count for given API keys."""
        result = await self.db.execute(
            select(func.count(AnalyticsEvent.id)).filter(
                AnalyticsEvent.api_key.in_(api_keys)
            )
        )
        return result.scalar()

    async def get_events_in_date_range_count(self, api_keys: List[str], 
                                           start_date: datetime, 
                                           end_date: datetime) -> int:
        """Get events count in date range for given API keys."""
        result = await self.db.execute(
            select(func.count(AnalyticsEvent.id)).filter(
                and_(
                    AnalyticsEvent.api_key.in_(api_keys),
                    AnalyticsEvent.event_timestamp >= start_date,
                    AnalyticsEvent.event_timestamp <= end_date,
                )
            )
        )
        return result.scalar()

    async def get_unique_python_versions_count(self, api_key: str, 
                                             start_date: datetime) -> int:
        """Get count of unique Python versions for an API key."""
        result = await self.db.execute(
            select(func.count(func.distinct(AnalyticsEvent.python_version))).filter(
                and_(
                    AnalyticsEvent.api_key == api_key,
                    AnalyticsEvent.event_timestamp >= start_date,
                )
            )
        )
        return result.scalar() or 0

    async def get_unique_os_count(self, api_key: str, start_date: datetime) -> int:
        """Get count of unique OS types for an API key."""
        result = await self.db.execute(
            select(func.count(func.distinct(AnalyticsEvent.os_type))).filter(
                and_(
                    AnalyticsEvent.api_key == api_key,
                    AnalyticsEvent.event_timestamp >= start_date,
                )
            )
        )
        return result.scalar() or 0

    async def get_sample_events(self, api_keys: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample events for debugging purposes."""
        sample_events_query = (
            select(
                AnalyticsEvent.event_timestamp,
                AnalyticsEvent.received_at,
                AnalyticsEvent.package_name,
            )
            .filter(AnalyticsEvent.api_key.in_(api_keys))
            .order_by(desc(AnalyticsEvent.received_at))
            .limit(limit)
        )

        result = await self.db.execute(sample_events_query)
        return [
            {
                "event_timestamp": row.event_timestamp,
                "received_at": row.received_at,
                "package_name": row.package_name
            }
            for row in result.all()
        ]

    async def create_analytics_event(self, api_key: str, session_id: str,
                                   package_name: str, package_version: str,
                                   python_version: str, os_type: str,
                                   event_timestamp: datetime) -> AnalyticsEvent:
        """Create a new analytics event."""
        return await self.create({
            "api_key": api_key,
            "session_id": session_id,
            "package_name": package_name,
            "package_version": package_version,
            "python_version": python_version,
            "os_type": os_type,
            "event_timestamp": event_timestamp
        })

    # Unique User Tracking Methods

    async def get_unique_users_count(
        self,
        api_keys: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """Get total unique users for given API keys within date range."""
        query = select(func.count(func.distinct(AnalyticsEvent.user_identifier))).filter(
            and_(
                AnalyticsEvent.api_key.in_(api_keys),
                AnalyticsEvent.user_identifier.isnot(None)
            )
        )

        if start_date:
            query = query.filter(AnalyticsEvent.event_timestamp >= start_date)
        if end_date:
            query = query.filter(AnalyticsEvent.event_timestamp <= end_date)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_active_users_by_period(
        self,
        api_keys: List[str],
        period_start: datetime,
        period_end: datetime
    ) -> int:
        """Get unique active users for a specific time period."""
        query = select(func.count(func.distinct(AnalyticsEvent.user_identifier))).filter(
            and_(
                AnalyticsEvent.api_key.in_(api_keys),
                AnalyticsEvent.user_identifier.isnot(None),
                AnalyticsEvent.event_timestamp >= period_start,
                AnalyticsEvent.event_timestamp <= period_end
            )
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_new_users_count(
        self,
        api_keys: List[str],
        period_start: datetime,
        period_end: datetime
    ) -> int:
        """Get count of new users (first seen) in the given period."""
        # Subquery to get first event timestamp for each user
        first_seen_subquery = (
            select(
                AnalyticsEvent.user_identifier,
                func.min(AnalyticsEvent.event_timestamp).label("first_seen")
            )
            .filter(
                and_(
                    AnalyticsEvent.api_key.in_(api_keys),
                    AnalyticsEvent.user_identifier.isnot(None)
                )
            )
            .group_by(AnalyticsEvent.user_identifier)
            .subquery()
        )

        # Count users whose first seen date is in the period
        query = select(func.count()).select_from(first_seen_subquery).filter(
            and_(
                first_seen_subquery.c.first_seen >= period_start,
                first_seen_subquery.c.first_seen <= period_end
            )
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_daily_active_users_timeseries(
        self,
        api_keys: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get daily active users time series."""
        query = (
            select(
                func.date(AnalyticsEvent.event_timestamp).label("date"),
                func.count(func.distinct(AnalyticsEvent.user_identifier)).label("unique_users")
            )
            .filter(
                and_(
                    AnalyticsEvent.api_key.in_(api_keys),
                    AnalyticsEvent.user_identifier.isnot(None),
                    AnalyticsEvent.event_timestamp >= start_date,
                    AnalyticsEvent.event_timestamp <= end_date
                )
            )
            .group_by(func.date(AnalyticsEvent.event_timestamp))
            .order_by(func.date(AnalyticsEvent.event_timestamp))
        )

        result = await self.db.execute(query)
        return [
            {
                "date": row.date,
                "unique_users": row.unique_users
            }
            for row in result.all()
        ]

    async def get_user_retention_stats(
        self,
        api_keys: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get user retention statistics."""
        # Get users with session counts
        user_sessions_query = (
            select(
                AnalyticsEvent.user_identifier,
                func.count(func.distinct(AnalyticsEvent.session_id)).label("session_count")
            )
            .filter(
                and_(
                    AnalyticsEvent.api_key.in_(api_keys),
                    AnalyticsEvent.user_identifier.isnot(None),
                    AnalyticsEvent.event_timestamp >= start_date,
                    AnalyticsEvent.event_timestamp <= end_date
                )
            )
            .group_by(AnalyticsEvent.user_identifier)
            .subquery()
        )

        # Count users by session categories
        stats_query = select(
            func.count().label("total_users"),
            func.sum(func.case((user_sessions_query.c.session_count == 1, 1), else_=0)).label("single_session"),
            func.sum(func.case((user_sessions_query.c.session_count > 1, 1), else_=0)).label("multi_session"),
            func.sum(func.case((user_sessions_query.c.session_count >= 10, 1), else_=0)).label("power_users"),
            func.avg(user_sessions_query.c.session_count).label("avg_sessions")
        ).select_from(user_sessions_query)

        result = await self.db.execute(stats_query)
        stats = result.first()

        return {
            "total_users": int(stats.total_users or 0),
            "single_session_users": int(stats.single_session or 0),
            "multi_session_users": int(stats.multi_session or 0),
            "power_users": int(stats.power_users or 0),
            "avg_sessions_per_user": float(stats.avg_sessions or 0)
        }

    async def get_unique_users_by_dimension(
        self,
        api_keys: List[str],
        dimension_field: str,  # e.g., "os_type", "python_version"
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get unique users broken down by a dimension (OS, Python version, etc.)."""
        # Validate dimension field against whitelist (security: prevent SQL injection)
        if dimension_field not in ALLOWED_DIMENSION_FIELDS:
            raise ValueError(
                f"Invalid dimension field: {dimension_field}. "
                f"Allowed fields: {', '.join(sorted(ALLOWED_DIMENSION_FIELDS))}"
            )

        # Map dimension field to model attribute
        dimension_column = getattr(AnalyticsEvent, dimension_field)

        query = (
            select(
                dimension_column.label("dimension_name"),
                func.count(func.distinct(AnalyticsEvent.user_identifier)).label("unique_users"),
                func.count(func.distinct(AnalyticsEvent.session_id)).label("total_sessions")
            )
            .filter(
                and_(
                    AnalyticsEvent.api_key.in_(api_keys),
                    AnalyticsEvent.user_identifier.isnot(None),
                    AnalyticsEvent.event_timestamp >= start_date,
                    AnalyticsEvent.event_timestamp <= end_date
                )
            )
            .group_by(dimension_column)
            .order_by(desc("unique_users"))
        )

        result = await self.db.execute(query)
        return [
            {
                "dimension_name": row.dimension_name,
                "unique_users": row.unique_users,
                "total_sessions": row.total_sessions,
                "avg_sessions_per_user": row.total_sessions / row.unique_users if row.unique_users > 0 else 0
            }
            for row in result.all()
        ]
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analytics_event import AnalyticsEvent
from src.repositories.base import BaseRepository


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
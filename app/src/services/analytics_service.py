from datetime import datetime, date, timedelta, timezone as tz
from typing import Optional, List, Dict, Any
import logging
from fastapi import HTTPException

from src.repositories.unit_of_work import AbstractUnitOfWork
from src.schemas.dashboard import (
    PackageOverview,
    TimeSeriesData,
    PythonVersionDistribution,
    OSDistribution,
    PackageVersionAdoption,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics data processing and aggregation."""

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def get_package_overview(self, user_id: int, package_name: Optional[str] = None) -> List[PackageOverview]:
        """Get overview statistics for user's packages."""
        # Get user's API keys
        api_keys = await self.uow.api_keys.get_user_api_keys_with_filter(user_id, package_name)
        
        if not api_keys:
            return []

        api_key_values = [key.key for key in api_keys]
        logger.info(f"Found {len(api_keys)} API keys for user {user_id} with package filter '{package_name}'")

        # Get date range - last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        # Convert to timezone-aware datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)

        # Check if we have any events in the current range
        events_in_range = await self.uow.analytics_events.get_events_in_date_range_count(
            api_key_values, start_datetime, end_datetime
        )
        
        # If no events in current range, extend to 90 days
        if events_in_range == 0:
            total_events = await self.uow.analytics_events.get_total_events_count(api_key_values)
            if total_events > 0:
                extended_start_date = end_date - timedelta(days=90)
                start_datetime = datetime.combine(extended_start_date, datetime.min.time()).replace(tzinfo=tz.utc)
                start_date = extended_start_date
                logger.info(f"No events in 30-day range, extending to 90 days: {extended_start_date} to {end_date}")

        # Aggregate stats per package
        overview_data = []

        for api_key in api_keys:
            # Get stats for this API key
            stats = await self.uow.analytics_events.get_stats_for_api_key(
                api_key.key, start_datetime, end_datetime
            )

            # Get Python version and OS counts
            python_version_count = await self.uow.analytics_events.get_unique_python_versions_count(
                api_key.key, start_datetime
            )
            os_count = await self.uow.analytics_events.get_unique_os_count(
                api_key.key, start_datetime
            )

            avg_daily_events = float(stats["total_events"]) / max(1, stats["active_days"])

            overview_data.append(
                PackageOverview(
                    package_name=api_key.package_name,
                    api_key=api_key.key,
                    total_events=stats["total_events"],
                    total_sessions=stats["total_sessions"],
                    avg_daily_events=round(avg_daily_events, 2),
                    active_days=stats["active_days"],
                    python_versions_count=python_version_count,
                    operating_systems_count=os_count,
                    date_range_start=start_date,
                    date_range_end=end_date,
                )
            )

        return overview_data

    async def get_timeseries_data(self, user_id: int, package_name: Optional[str] = None,
                                 start_date: Optional[date] = None, 
                                 end_date: Optional[date] = None) -> TimeSeriesData:
        """Get time-series data for package usage over time."""
        # Default to last 30 days if no date range provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Convert to timezone-aware datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)

        # Get user's API keys
        api_keys = await self.uow.api_keys.get_user_api_keys_with_filter(user_id, package_name)
        
        if not api_keys:
            return TimeSeriesData(dates=[], events=[], sessions=[], packages=[])

        api_key_values = [key.key for key in api_keys]

        # Get daily aggregated data
        daily_stats = await self.uow.analytics_events.get_daily_timeseries(
            api_key_values, start_datetime, end_datetime
        )

        # Organize data by date
        dates_data = {}
        package_names = set()

        for stat in daily_stats:
            date_str = stat["date"].isoformat()
            package_names.add(stat["package_name"])

            if date_str not in dates_data:
                dates_data[date_str] = {"events": 0, "sessions": 0, "packages": {}}

            dates_data[date_str]["events"] += stat["total_events"]
            dates_data[date_str]["sessions"] += stat["total_sessions"]
            dates_data[date_str]["packages"][stat["package_name"]] = {
                "events": stat["total_events"],
                "sessions": stat["total_sessions"],
            }

        # Convert to lists for frontend consumption
        sorted_dates = sorted(dates_data.keys())

        return TimeSeriesData(
            dates=sorted_dates,
            events=[dates_data[d]["events"] for d in sorted_dates],
            sessions=[dates_data[d]["sessions"] for d in sorted_dates],
            packages=list(package_names),
            package_data=dates_data,
        )

    async def get_python_version_distribution(self, user_id: int, package_name: Optional[str] = None,
                                            start_date: Optional[date] = None,
                                            end_date: Optional[date] = None) -> List[PythonVersionDistribution]:
        """Get Python version distribution for packages."""
        # Default to last 30 days
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Convert to timezone-aware datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)

        # Get user's API keys
        api_keys = await self.uow.api_keys.get_user_api_keys_with_filter(user_id, package_name)
        
        if not api_keys:
            return []

        api_key_values = [key.key for key in api_keys]

        # Get Python version distribution
        python_stats = await self.uow.analytics_events.get_python_version_distribution(
            api_key_values, start_datetime, end_datetime
        )

        # Calculate percentages
        total_events = sum(stat["total_events"] for stat in python_stats)
        total_sessions = sum(stat["total_sessions"] for stat in python_stats)

        result = []
        for stat in python_stats:
            event_percentage = (stat["total_events"] / total_events * 100) if total_events > 0 else 0
            session_percentage = (stat["total_sessions"] / total_sessions * 100) if total_sessions > 0 else 0

            result.append(
                PythonVersionDistribution(
                    python_version=stat["python_version"],
                    event_count=stat["total_events"],
                    session_count=stat["total_sessions"],
                    event_percentage=round(event_percentage, 2),
                    session_percentage=round(session_percentage, 2),
                )
            )

        return result

    async def get_os_distribution(self, user_id: int, package_name: Optional[str] = None,
                                 start_date: Optional[date] = None,
                                 end_date: Optional[date] = None) -> List[OSDistribution]:
        """Get operating system distribution for packages."""
        # Default to last 30 days
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Convert to timezone-aware datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)

        # Get user's API keys
        api_keys = await self.uow.api_keys.get_user_api_keys_with_filter(user_id, package_name)
        
        if not api_keys:
            return []

        api_key_values = [key.key for key in api_keys]

        # Get OS distribution
        os_stats = await self.uow.analytics_events.get_os_distribution(
            api_key_values, start_datetime, end_datetime
        )

        # Calculate percentages
        total_events = sum(stat["total_events"] for stat in os_stats)
        total_sessions = sum(stat["total_sessions"] for stat in os_stats)

        result = []
        for stat in os_stats:
            event_percentage = (stat["total_events"] / total_events * 100) if total_events > 0 else 0
            session_percentage = (stat["total_sessions"] / total_sessions * 100) if total_sessions > 0 else 0

            result.append(
                OSDistribution(
                    os_type=stat["os_type"],
                    event_count=stat["total_events"],
                    session_count=stat["total_sessions"],
                    event_percentage=round(event_percentage, 2),
                    session_percentage=round(session_percentage, 2),
                )
            )

        return result

    async def get_package_version_adoption(self, user_id: int, package_name: str,
                                         start_date: Optional[date] = None,
                                         end_date: Optional[date] = None) -> List[PackageVersionAdoption]:
        """Get package version adoption statistics."""
        # Default to last 30 days
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Convert to timezone-aware datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)

        # Get user's API key for this package
        api_key = await self.uow.api_keys.get_by_user_and_package(user_id, package_name)
        
        if not api_key:
            raise HTTPException(status_code=404, detail="Package not found")

        # Get package version distribution
        version_stats = await self.uow.analytics_events.get_package_version_distribution(
            api_key.key, start_datetime, end_datetime
        )

        # Calculate percentages
        total_events = sum(stat["total_events"] for stat in version_stats)
        total_sessions = sum(stat["total_sessions"] for stat in version_stats)

        result = []
        for stat in version_stats:
            event_percentage = (stat["total_events"] / total_events * 100) if total_events > 0 else 0
            session_percentage = (stat["total_sessions"] / total_sessions * 100) if total_sessions > 0 else 0

            result.append(
                PackageVersionAdoption(
                    package_version=stat["package_version"],
                    event_count=stat["total_events"],
                    session_count=stat["total_sessions"],
                    event_percentage=round(event_percentage, 2),
                    session_percentage=round(session_percentage, 2),
                    is_latest_version=None,  # We don't track this in raw data anymore
                )
            )

        return result

    async def create_analytics_event(self, api_key: str, session_id: str, 
                                   package_name: str, package_version: str,
                                   python_version: str, os_type: str,
                                   event_timestamp: datetime) -> None:
        """Create a new analytics event."""
        await self.uow.analytics_events.create_analytics_event(
            api_key=api_key,
            session_id=session_id,
            package_name=package_name,
            package_version=package_version,
            python_version=python_version,
            os_type=os_type,
            event_timestamp=event_timestamp
        )
        await self.uow.commit()
        logger.debug(f"Analytics event created for package {package_name}")

    async def get_analytics_summary_for_user(self, user_id: int) -> Dict[str, Any]:
        """Get a comprehensive analytics summary for a user."""
        api_keys = await self.uow.api_keys.get_active_keys_by_user(user_id)
        
        if not api_keys:
            return {
                "total_packages": 0,
                "total_events": 0,
                "total_sessions": 0,
                "packages": []
            }

        api_key_values = [key.key for key in api_keys]
        
        # Get total events across all packages
        total_events = await self.uow.analytics_events.get_total_events_count(api_key_values)
        
        # Get package-specific data
        packages_data = []
        for api_key in api_keys:
            # Get recent stats for this package
            end_date = datetime.now(tz.utc)
            start_date = end_date - timedelta(days=30)
            
            stats = await self.uow.analytics_events.get_stats_for_api_key(
                api_key.key, start_date, end_date
            )
            
            packages_data.append({
                "package_name": api_key.package_name,
                "api_key": api_key.key,
                "events": stats["total_events"],
                "sessions": stats["total_sessions"],
                "active_days": stats["active_days"]
            })

        total_sessions = sum(pkg["sessions"] for pkg in packages_data)

        return {
            "total_packages": len(api_keys),
            "total_events": total_events,
            "total_sessions": total_sessions,
            "packages": packages_data
        }
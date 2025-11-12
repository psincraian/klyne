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
    UniqueUsersOverview,
    ActiveUsersTimeSeries,
    UserRetentionMetrics,
    UniqueUsersByDimension,
    CustomEventType,
    CustomEventTimeSeries,
    CustomEventDetails,
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

            # Get unique users count for this API key
            unique_users = await self.uow.analytics_events.get_unique_users_count(
                [api_key.key], start_datetime, end_datetime
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
                    total_unique_users=unique_users,
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
            return TimeSeriesData(dates=[], events=[], sessions=[], unique_users=[], packages=[])

        api_key_values = [key.key for key in api_keys]

        # Get daily aggregated data
        daily_stats = await self.uow.analytics_events.get_daily_timeseries(
            api_key_values, start_datetime, end_datetime
        )

        # Get daily unique users data
        daily_unique_users = await self.uow.analytics_events.get_daily_active_users_timeseries(
            api_key_values, start_datetime, end_datetime
        )

        # Create a map of date -> unique_users for quick lookup
        unique_users_map = {
            item["date"].isoformat(): item["unique_users"]
            for item in daily_unique_users
        }

        # Organize data by date
        dates_data = {}
        package_names = set()

        for stat in daily_stats:
            date_str = stat["date"].isoformat()
            package_names.add(stat["package_name"])

            if date_str not in dates_data:
                dates_data[date_str] = {
                    "events": 0,
                    "sessions": 0,
                    "unique_users": unique_users_map.get(date_str, 0),
                    "packages": {}
                }

            dates_data[date_str]["events"] += stat["total_events"]
            dates_data[date_str]["sessions"] += stat["total_sessions"]
            dates_data[date_str]["packages"][stat["package_name"]] = {
                "events": stat["total_events"],
                "sessions": stat["total_sessions"],
            }

        # Build complete date range (fill gaps with zeros)
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date.isoformat())
            current_date += timedelta(days=1)

        # Fill in missing dates with zeros
        events_list = []
        sessions_list = []
        unique_users_list = []

        for date_str in date_range:
            if date_str in dates_data:
                events_list.append(dates_data[date_str]["events"])
                sessions_list.append(dates_data[date_str]["sessions"])
                unique_users_list.append(dates_data[date_str]["unique_users"])
            else:
                events_list.append(0)
                sessions_list.append(0)
                unique_users_list.append(0)

        return TimeSeriesData(
            dates=date_range,
            events=events_list,
            sessions=sessions_list,
            unique_users=unique_users_list,
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

    # Unique User Tracking Methods

    async def get_unique_users_overview(
        self,
        user_id: int,
        package_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> UniqueUsersOverview:
        """Get overview of unique users for user's packages."""
        # Default date range
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Convert to timezone-aware datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)
        now = datetime.now(tz.utc)

        # Get user's API keys
        api_keys = await self.uow.api_keys.get_user_api_keys_with_filter(user_id, package_name)

        if not api_keys:
            return UniqueUsersOverview(
                package_name=package_name or "all_packages",
                total_unique_users=0,
                daily_active_users=0,
                weekly_active_users=0,
                monthly_active_users=0,
                new_users_today=0,
                new_users_this_week=0,
                new_users_this_month=0,
                growth_rate_daily=None,
                growth_rate_weekly=None,
                growth_rate_monthly=None,
                date_range_start=start_date,
                date_range_end=end_date,
            )

        api_key_values = [key.key for key in api_keys]

        # Get total unique users (all time within date range)
        total_unique = await self.uow.analytics_events.get_unique_users_count(
            api_key_values, start_datetime, end_datetime
        )

        # Get DAU (last 24 hours)
        dau_start = now - timedelta(days=1)
        daily_active = await self.uow.analytics_events.get_active_users_by_period(
            api_key_values, dau_start, now
        )

        # Get WAU (last 7 days)
        wau_start = now - timedelta(days=7)
        weekly_active = await self.uow.analytics_events.get_active_users_by_period(
            api_key_values, wau_start, now
        )

        # Get MAU (last 30 days)
        mau_start = now - timedelta(days=30)
        monthly_active = await self.uow.analytics_events.get_active_users_by_period(
            api_key_values, mau_start, now
        )

        # Get new users - today
        today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=tz.utc)
        today_end = datetime.combine(date.today(), datetime.max.time()).replace(tzinfo=tz.utc)
        new_users_today = await self.uow.analytics_events.get_new_users_count(
            api_key_values, today_start, today_end
        )

        # Get new users - this week
        week_start = today_start - timedelta(days=7)
        new_users_week = await self.uow.analytics_events.get_new_users_count(
            api_key_values, week_start, now
        )

        # Get new users - this month
        month_start = today_start - timedelta(days=30)
        new_users_month = await self.uow.analytics_events.get_new_users_count(
            api_key_values, month_start, now
        )

        # Calculate growth rates (compare to previous period)
        # Daily growth rate
        yesterday_start = dau_start - timedelta(days=1)
        yesterday_active = await self.uow.analytics_events.get_active_users_by_period(
            api_key_values, yesterday_start, dau_start
        )
        daily_growth = ((daily_active - yesterday_active) / yesterday_active * 100) if yesterday_active > 0 else None

        # Weekly growth rate
        prev_week_start = wau_start - timedelta(days=7)
        prev_week_active = await self.uow.analytics_events.get_active_users_by_period(
            api_key_values, prev_week_start, wau_start
        )
        weekly_growth = ((weekly_active - prev_week_active) / prev_week_active * 100) if prev_week_active > 0 else None

        # Monthly growth rate
        prev_month_start = mau_start - timedelta(days=30)
        prev_month_active = await self.uow.analytics_events.get_active_users_by_period(
            api_key_values, prev_month_start, mau_start
        )
        monthly_growth = ((monthly_active - prev_month_active) / prev_month_active * 100) if prev_month_active > 0 else None

        logger.info(f"Unique users overview for user {user_id}: {total_unique} total, {daily_active} DAU, {weekly_active} WAU, {monthly_active} MAU")

        return UniqueUsersOverview(
            package_name=package_name or "all_packages",
            total_unique_users=total_unique,
            daily_active_users=daily_active,
            weekly_active_users=weekly_active,
            monthly_active_users=monthly_active,
            new_users_today=new_users_today,
            new_users_this_week=new_users_week,
            new_users_this_month=new_users_month,
            growth_rate_daily=round(daily_growth, 2) if daily_growth is not None else None,
            growth_rate_weekly=round(weekly_growth, 2) if weekly_growth is not None else None,
            growth_rate_monthly=round(monthly_growth, 2) if monthly_growth is not None else None,
            date_range_start=start_date,
            date_range_end=end_date,
        )

    async def get_active_users_timeseries(
        self,
        user_id: int,
        package_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> ActiveUsersTimeSeries:
        """Get time series data for active users."""
        # Default date range
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
            return ActiveUsersTimeSeries(
                dates=[],
                daily_active_users=[],
                weekly_active_users=[],
                monthly_active_users=[],
                new_users=[],
                returning_users=[]
            )

        api_key_values = [key.key for key in api_keys]

        # Get daily active users
        daily_data = await self.uow.analytics_events.get_daily_active_users_timeseries(
            api_key_values, start_datetime, end_datetime
        )

        # Build date list
        dates = [item["date"].isoformat() for item in daily_data]
        daily_active = [item["unique_users"] for item in daily_data]

        # Calculate WAU and MAU for each date (rolling windows)
        weekly_active = []
        monthly_active = []
        new_users = []
        returning_users = []

        for item in daily_data:
            current_date = datetime.combine(item["date"], datetime.max.time()).replace(tzinfo=tz.utc)

            # WAU - 7 day window
            wau_start = current_date - timedelta(days=7)
            wau_count = await self.uow.analytics_events.get_active_users_by_period(
                api_key_values, wau_start, current_date
            )
            weekly_active.append(wau_count)

            # MAU - 30 day window
            mau_start = current_date - timedelta(days=30)
            mau_count = await self.uow.analytics_events.get_active_users_by_period(
                api_key_values, mau_start, current_date
            )
            monthly_active.append(mau_count)

            # New users for this date
            day_start = datetime.combine(item["date"], datetime.min.time()).replace(tzinfo=tz.utc)
            day_end = datetime.combine(item["date"], datetime.max.time()).replace(tzinfo=tz.utc)
            new_count = await self.uow.analytics_events.get_new_users_count(
                api_key_values, day_start, day_end
            )
            new_users.append(new_count)

            # Returning users = DAU - new users
            returning = max(0, item["unique_users"] - new_count)
            returning_users.append(returning)

        return ActiveUsersTimeSeries(
            dates=dates,
            daily_active_users=daily_active,
            weekly_active_users=weekly_active,
            monthly_active_users=monthly_active,
            new_users=new_users,
            returning_users=returning_users
        )

    async def get_user_retention_metrics(
        self,
        user_id: int,
        package_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> UserRetentionMetrics:
        """Get user retention and engagement metrics."""
        # Default date range
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
            return UserRetentionMetrics(
                total_users=0,
                new_users=0,
                returning_users=0,
                retention_rate=0,
                avg_sessions_per_user=0,
                single_session_users=0,
                multi_session_users=0,
                power_users=0
            )

        api_key_values = [key.key for key in api_keys]

        # Get retention stats from repository
        stats = await self.uow.analytics_events.get_user_retention_stats(
            api_key_values, start_datetime, end_datetime
        )

        # Get new users in this period
        new_users = await self.uow.analytics_events.get_new_users_count(
            api_key_values, start_datetime, end_datetime
        )

        # Calculate returning users and retention rate
        returning_users = stats["total_users"] - new_users
        retention_rate = (returning_users / stats["total_users"] * 100) if stats["total_users"] > 0 else 0

        return UserRetentionMetrics(
            total_users=stats["total_users"],
            new_users=new_users,
            returning_users=max(0, returning_users),
            retention_rate=round(retention_rate, 2),
            avg_sessions_per_user=round(stats["avg_sessions_per_user"], 2),
            single_session_users=stats["single_session_users"],
            multi_session_users=stats["multi_session_users"],
            power_users=stats["power_users"]
        )

    async def get_unique_users_by_os(
        self,
        user_id: int,
        package_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[UniqueUsersByDimension]:
        """Get unique users broken down by operating system."""
        return await self._get_unique_users_by_dimension(
            user_id, "os_type", package_name, start_date, end_date
        )

    async def get_unique_users_by_python_version(
        self,
        user_id: int,
        package_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[UniqueUsersByDimension]:
        """Get unique users broken down by Python version."""
        return await self._get_unique_users_by_dimension(
            user_id, "python_version", package_name, start_date, end_date
        )

    async def _get_unique_users_by_dimension(
        self,
        user_id: int,
        dimension_field: str,
        package_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[UniqueUsersByDimension]:
        """Internal method to get unique users by any dimension."""
        # Default date range
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

        # Get dimension breakdown from repository
        dimension_stats = await self.uow.analytics_events.get_unique_users_by_dimension(
            api_key_values, dimension_field, start_datetime, end_datetime
        )

        # Calculate percentages
        total_unique_users = sum(stat["unique_users"] for stat in dimension_stats)

        result = []
        for stat in dimension_stats:
            percentage = (stat["unique_users"] / total_unique_users * 100) if total_unique_users > 0 else 0
            result.append(
                UniqueUsersByDimension(
                    dimension_name=str(stat["dimension_name"]),
                    unique_users=stat["unique_users"],
                    percentage=round(percentage, 2),
                    avg_sessions_per_user=round(stat["avg_sessions_per_user"], 2)
                )
            )

        return result

    async def get_custom_event_types(self, api_keys: List[str],
                                    start_date: datetime,
                                    end_date: datetime) -> List[CustomEventType]:
        """Get all custom event types with their counts."""
        from src.schemas.dashboard import CustomEventType

        event_types = await self.uow.analytics_events.get_custom_event_types(
            api_keys, start_date, end_date
        )

        return [
            CustomEventType(
                event_type=event["event_type"],
                total_count=event["total_count"]
            )
            for event in event_types
        ]

    async def get_custom_events_timeseries(self, api_keys: List[str],
                                          event_types: List[str],
                                          start_date: datetime,
                                          end_date: datetime) -> CustomEventTimeSeries:
        """Get time series data for selected custom event types."""
        from src.schemas.dashboard import CustomEventTimeSeries
        from collections import defaultdict

        # Get raw time series data
        raw_data = await self.uow.analytics_events.get_custom_events_timeseries(
            api_keys, event_types, start_date, end_date
        )

        # Build date range
        date_range = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_range.append(current_date.isoformat())
            current_date += timedelta(days=1)

        # Organize data by event type
        data_by_type = defaultdict(lambda: defaultdict(int))
        for row in raw_data:
            date_str = row["date"].isoformat()
            event_type = row["event_type"]
            count = row["count"]
            data_by_type[event_type][date_str] = count

        # Build series data with zeros for missing dates
        series_data = {}
        for event_type in event_types:
            series_data[event_type] = [
                data_by_type[event_type].get(date_str, 0)
                for date_str in date_range
            ]

        return CustomEventTimeSeries(
            dates=date_range,
            event_types=event_types,
            series_data=series_data
        )

    async def get_custom_event_details(self, api_keys: List[str],
                                      event_type: str,
                                      start_date: datetime,
                                      end_date: datetime) -> CustomEventDetails:
        """Get detailed information about a specific custom event type."""
        from src.schemas.dashboard import CustomEventDetails, CustomEventProperty

        # Get event count
        event_types_data = await self.uow.analytics_events.get_custom_event_types(
            api_keys, start_date, end_date
        )

        total_count = 0
        for event_data in event_types_data:
            if event_data["event_type"] == event_type:
                total_count = event_data["total_count"]
                break

        # Get property samples
        properties_data = await self.uow.analytics_events.get_custom_event_properties(
            api_keys, event_type, start_date, end_date, limit=10
        )

        sample_properties = [
            CustomEventProperty(
                properties=prop["properties"],
                timestamp=prop["timestamp"].isoformat()
            )
            for prop in properties_data
        ]

        return CustomEventDetails(
            event_type=event_type,
            total_count=total_count,
            sample_properties=sample_properties
        )

    async def get_custom_event_types_for_user(self, user_id: int,
                                              package_name: Optional[str] = None,
                                              start_date: Optional[date] = None,
                                              end_date: Optional[date] = None) -> List[CustomEventType]:
        """Get custom event types for a user's packages."""
        # Get user's API keys
        api_keys = await self.uow.api_keys.get_user_api_keys_with_filter(user_id, package_name)

        if not api_keys:
            return []

        api_key_values = [key.key for key in api_keys]

        # Use default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Convert to datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)

        return await self.get_custom_event_types(api_key_values, start_datetime, end_datetime)

    async def get_custom_events_timeseries_for_user(self, user_id: int,
                                                   event_types: List[str],
                                                   package_name: Optional[str] = None,
                                                   start_date: Optional[date] = None,
                                                   end_date: Optional[date] = None) -> CustomEventTimeSeries:
        """Get custom events timeseries for a user's packages."""
        # Get user's API keys
        api_keys = await self.uow.api_keys.get_user_api_keys_with_filter(user_id, package_name)

        if not api_keys:
            # Return empty time series
            return CustomEventTimeSeries(dates=[], event_types=event_types, series_data={})

        api_key_values = [key.key for key in api_keys]

        # Use default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Convert to datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)

        return await self.get_custom_events_timeseries(api_key_values, event_types, start_datetime, end_datetime)

    async def get_custom_event_details_for_user(self, user_id: int,
                                               event_type: str,
                                               package_name: Optional[str] = None,
                                               start_date: Optional[date] = None,
                                               end_date: Optional[date] = None) -> CustomEventDetails:
        """Get custom event details for a user's packages."""
        # Get user's API keys
        api_keys = await self.uow.api_keys.get_user_api_keys_with_filter(user_id, package_name)

        if not api_keys:
            # Return empty details
            return CustomEventDetails(event_type=event_type, total_count=0, sample_properties=[])

        api_key_values = [key.key for key in api_keys]

        # Use default date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Convert to datetime
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)

        return await self.get_custom_event_details(api_key_values, event_type, start_datetime, end_datetime)
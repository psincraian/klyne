"""
Dashboard API endpoints for analytics data.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import aliased
import logging
from src.core.database import get_db
from src.core.auth import get_current_user_id, require_authentication
from src.models.api_key import APIKey
from src.models.analytics_event import AnalyticsEvent
from src.schemas.dashboard import (
    PackageOverview,
    TimeSeriesData,
    PythonVersionDistribution,
    OSDistribution,
    PackageVersionAdoption,
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

logger = logging.getLogger(__name__)

@router.get("/overview")
async def get_dashboard_overview(
    package_name: Optional[str] = Query(None, description="Filter by package name"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_authentication)
) -> List[PackageOverview]:
    """
    Get overview statistics for all user's packages or a specific package.
    """
    # Get user's API keys to filter data
    api_keys_query = select(APIKey).filter(APIKey.user_id == user_id)
    if package_name:
        api_keys_query = api_keys_query.filter(APIKey.package_name == package_name)
    
    api_keys_result = await db.execute(api_keys_query)
    api_keys = api_keys_result.scalars().all()
    logger.info(f"Found {len(api_keys)} API keys for user {user_id} with package filter '{package_name}'")
    if not api_keys:
        return []
    
    api_key_values = [key.key for key in api_keys]
    logger.info(f"API key values: {api_key_values}")
    
    # Get last 30 days of data with timezone awareness
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Convert to datetime with timezone for proper comparison
    from datetime import timezone as tz
    start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)
    
    logger.info(f"Date range: {start_date} to {end_date} (converted to UTC: {start_datetime} to {end_datetime})")
    
    # Debug: Check total events in database for these API keys
    total_events_query = select(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.api_key.in_(api_key_values)
    )
    total_events_result = await db.execute(total_events_query)
    total_events = total_events_result.scalar()
    logger.info(f"Total events in database for user's API keys: {total_events}")
    
    # Debug: Check events in date range
    events_in_range_query = select(func.count(AnalyticsEvent.id)).filter(
        and_(
            AnalyticsEvent.api_key.in_(api_key_values),
            AnalyticsEvent.event_timestamp >= start_datetime,
            AnalyticsEvent.event_timestamp <= end_datetime
        )
    )
    events_in_range_result = await db.execute(events_in_range_query)
    events_in_range = events_in_range_result.scalar()
    logger.info(f"Events in date range {start_date} to {end_date}: {events_in_range}")
    
    # Debug: Check actual event timestamps to see when they were created
    sample_events_query = select(
        AnalyticsEvent.event_timestamp,
        AnalyticsEvent.received_at,
        AnalyticsEvent.package_name
    ).filter(
        AnalyticsEvent.api_key.in_(api_key_values)
    ).order_by(desc(AnalyticsEvent.received_at)).limit(5)
    
    sample_events_result = await db.execute(sample_events_query)
    sample_events = sample_events_result.all()
    
    for event in sample_events:
        logger.info(f"Sample event: {event.package_name} - event_timestamp: {event.event_timestamp}, received_at: {event.received_at}")
    
    # If no events in current range, extend the range to 90 days
    if events_in_range == 0 and total_events > 0:
        extended_start_date = end_date - timedelta(days=90)
        start_datetime = datetime.combine(extended_start_date, datetime.min.time()).replace(tzinfo=tz.utc)
        logger.info(f"No events in 30-day range, extending to 90 days: {extended_start_date} to {end_date}")
        start_date = extended_start_date
    
    # Aggregate stats per package
    overview_data = []
    
    for api_key in api_keys:
        # Get total events and sessions for this package in last 30 days from raw data
        stats_query = select(
            func.count(AnalyticsEvent.id).label('total_events'),
            func.count(func.distinct(AnalyticsEvent.session_id)).label('total_sessions'),
            func.count(func.distinct(func.date(AnalyticsEvent.event_timestamp))).label('active_days')
        ).filter(
            and_(
                AnalyticsEvent.api_key == api_key.key,
                AnalyticsEvent.event_timestamp >= start_datetime,
                AnalyticsEvent.event_timestamp <= end_datetime
            )
        )

        logger.info(f"Running stats query for package {api_key.package_name} from {start_date} to {end_date}")
        
        stats_result = await db.execute(stats_query)
        stats = stats_result.first()
        
        logger.info(f"Stats result for {api_key.package_name}: total_events={stats.total_events}, total_sessions={stats.total_sessions}, active_days={stats.active_days}")
        
        # Get Python version count
        python_versions_query = select(
            func.count(func.distinct(AnalyticsEvent.python_version))
        ).filter(
            and_(
                AnalyticsEvent.api_key == api_key.key,
                AnalyticsEvent.event_timestamp >= start_datetime
            )
        )
        python_versions_result = await db.execute(python_versions_query)
        python_version_count = python_versions_result.scalar() or 0
        
        # Get OS count
        os_query = select(
            func.count(func.distinct(AnalyticsEvent.os_type))
        ).filter(
            and_(
                AnalyticsEvent.api_key == api_key.key,
                AnalyticsEvent.event_timestamp >= start_datetime
            )
        )
        os_result = await db.execute(os_query)
        os_count = os_result.scalar() or 0
        
        avg_daily_events = float(stats.total_events or 0) / max(1, stats.active_days or 1)
        
        overview_data.append(PackageOverview(
            package_name=api_key.package_name,
            api_key=api_key.key,
            total_events=int(stats.total_events or 0),
            total_sessions=int(stats.total_sessions or 0),
            avg_daily_events=round(avg_daily_events, 2),
            active_days=int(stats.active_days or 0),
            python_versions_count=python_version_count,
            operating_systems_count=os_count,
            date_range_start=start_date,
            date_range_end=end_date
        ))
    
    return overview_data


@router.get("/timeseries")
async def get_timeseries_data(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_authentication)
) -> TimeSeriesData:
    """
    Get time-series data for package usage over time.
    """
    # Default to last 30 days if no date range provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Convert to timezone-aware datetime for proper comparison
    from datetime import timezone as tz
    start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)
    
    # Get user's API keys
    api_keys_query = select(APIKey).filter(APIKey.user_id == user_id)
    if package_name:
        api_keys_query = api_keys_query.filter(APIKey.package_name == package_name)
    
    api_keys_result = await db.execute(api_keys_query)
    api_keys = api_keys_result.scalars().all()
    
    if not api_keys:
        return TimeSeriesData(
            dates=[],
            events=[],
            sessions=[],
            packages=[]
        )
    
    api_key_values = [key.key for key in api_keys]
    
    # Get daily aggregated data from raw events
    daily_stats_query = select(
        func.date(AnalyticsEvent.event_timestamp).label('date'),
        AnalyticsEvent.package_name,
        func.count(AnalyticsEvent.id).label('total_events'),
        func.count(func.distinct(AnalyticsEvent.session_id)).label('total_sessions')
    ).filter(
        and_(
            AnalyticsEvent.api_key.in_(api_key_values),
            AnalyticsEvent.event_timestamp >= start_datetime,
            AnalyticsEvent.event_timestamp <= end_datetime
        )
    ).group_by(
        func.date(AnalyticsEvent.event_timestamp),
        AnalyticsEvent.package_name
    ).order_by(func.date(AnalyticsEvent.event_timestamp))
    
    daily_stats_result = await db.execute(daily_stats_query)
    daily_stats = daily_stats_result.all()
    
    # Organize data by date
    dates_data = {}
    package_names = set()
    
    for stat in daily_stats:
        date_str = stat.date.isoformat()
        package_names.add(stat.package_name)
        
        if date_str not in dates_data:
            dates_data[date_str] = {
                'events': 0,
                'sessions': 0,
                'packages': {}
            }
        
        dates_data[date_str]['events'] += stat.total_events
        dates_data[date_str]['sessions'] += stat.total_sessions
        dates_data[date_str]['packages'][stat.package_name] = {
            'events': stat.total_events,
            'sessions': stat.total_sessions
        }
    
    # Convert to lists for frontend consumption
    sorted_dates = sorted(dates_data.keys())
    
    return TimeSeriesData(
        dates=sorted_dates,
        events=[dates_data[d]['events'] for d in sorted_dates],
        sessions=[dates_data[d]['sessions'] for d in sorted_dates],
        packages=list(package_names),
        package_data=dates_data
    )


@router.get("/python-versions")
async def get_python_version_distribution(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_authentication)
) -> List[PythonVersionDistribution]:
    """
    Get Python version distribution for packages.
    """
    # Default to last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Convert to timezone-aware datetime for proper comparison
    from datetime import timezone as tz
    start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)
    
    # Get user's API keys
    api_keys_query = select(APIKey).filter(APIKey.user_id == user_id)
    if package_name:
        api_keys_query = api_keys_query.filter(APIKey.package_name == package_name)
    
    api_keys_result = await db.execute(api_keys_query)
    api_keys = api_keys_result.scalars().all()
    
    if not api_keys:
        return []
    
    api_key_values = [key.key for key in api_keys]
    
    # Aggregate Python version stats from raw data
    python_stats_query = select(
        AnalyticsEvent.python_version,
        func.count(AnalyticsEvent.id).label('total_events'),
        func.count(func.distinct(AnalyticsEvent.session_id)).label('total_sessions')
    ).filter(
        and_(
            AnalyticsEvent.api_key.in_(api_key_values),
            AnalyticsEvent.event_timestamp >= start_datetime,
            AnalyticsEvent.event_timestamp <= end_datetime
        )
    ).group_by(AnalyticsEvent.python_version).order_by(desc('total_events'))
    
    python_stats_result = await db.execute(python_stats_query)
    python_stats = python_stats_result.all()
    
    # Calculate percentages
    total_events = sum(stat.total_events for stat in python_stats)
    total_sessions = sum(stat.total_sessions for stat in python_stats)
    
    result = []
    for stat in python_stats:
        event_percentage = (stat.total_events / total_events * 100) if total_events > 0 else 0
        session_percentage = (stat.total_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        result.append(PythonVersionDistribution(
            python_version=stat.python_version,
            event_count=stat.total_events,
            session_count=stat.total_sessions,
            event_percentage=round(event_percentage, 2),
            session_percentage=round(session_percentage, 2)
        ))
    
    return result


@router.get("/operating-systems")
async def get_os_distribution(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_authentication)
) -> List[OSDistribution]:
    """
    Get operating system distribution for packages.
    """
    # Default to last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Convert to timezone-aware datetime for proper comparison
    from datetime import timezone as tz
    start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)
    
    # Get user's API keys
    api_keys_query = select(APIKey).filter(APIKey.user_id == user_id)
    if package_name:
        api_keys_query = api_keys_query.filter(APIKey.package_name == package_name)
    
    api_keys_result = await db.execute(api_keys_query)
    api_keys = api_keys_result.scalars().all()
    
    if not api_keys:
        return []
    
    api_key_values = [key.key for key in api_keys]
    
    # Aggregate OS stats from raw data
    os_stats_query = select(
        AnalyticsEvent.os_type,
        func.count(AnalyticsEvent.id).label('total_events'),
        func.count(func.distinct(AnalyticsEvent.session_id)).label('total_sessions')
    ).filter(
        and_(
            AnalyticsEvent.api_key.in_(api_key_values),
            AnalyticsEvent.event_timestamp >= start_datetime,
            AnalyticsEvent.event_timestamp <= end_datetime
        )
    ).group_by(AnalyticsEvent.os_type).order_by(desc('total_events'))
    
    os_stats_result = await db.execute(os_stats_query)
    os_stats = os_stats_result.all()
    
    # Calculate percentages
    total_events = sum(stat.total_events for stat in os_stats)
    total_sessions = sum(stat.total_sessions for stat in os_stats)
    
    result = []
    for stat in os_stats:
        event_percentage = (stat.total_events / total_events * 100) if total_events > 0 else 0
        session_percentage = (stat.total_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        result.append(OSDistribution(
            os_type=stat.os_type,
            event_count=stat.total_events,
            session_count=stat.total_sessions,
            event_percentage=round(event_percentage, 2),
            session_percentage=round(session_percentage, 2)
        ))
    
    return result


@router.get("/package-versions")
async def get_package_version_adoption(
    package_name: str = Query(..., description="Package name to analyze"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_authentication)
) -> List[PackageVersionAdoption]:
    """
    Get package version adoption statistics.
    """
    # Default to last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Convert to timezone-aware datetime for proper comparison
    from datetime import timezone as tz
    start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=tz.utc)
    end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=tz.utc)
    
    # Get user's API key for this package
    api_key_query = select(APIKey).filter(
        and_(
            APIKey.user_id == user_id,
            APIKey.package_name == package_name
        )
    )
    api_key_result = await db.execute(api_key_query)
    api_key = api_key_result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="Package not found")

    logger.info(f"Fetching package version adoption for {package_name} from {start_date} to {end_date}")
    # Get package version stats from raw data
    version_stats_query = select(
        AnalyticsEvent.package_version,
        func.count(AnalyticsEvent.id).label('total_events'),
        func.count(func.distinct(AnalyticsEvent.session_id)).label('total_sessions')
    ).filter(
        and_(
            AnalyticsEvent.api_key == api_key.key,
            AnalyticsEvent.event_timestamp >= start_datetime,
            AnalyticsEvent.event_timestamp <= end_datetime
        )
    ).group_by(AnalyticsEvent.package_version).order_by(desc('total_events'))
    
    version_stats_result = await db.execute(version_stats_query)
    version_stats = version_stats_result.all()
    
    # Calculate percentages
    total_events = sum(stat.total_events for stat in version_stats)
    total_sessions = sum(stat.total_sessions for stat in version_stats)
    
    result = []
    for stat in version_stats:
        event_percentage = (stat.total_events / total_events * 100) if total_events > 0 else 0
        session_percentage = (stat.total_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        result.append(PackageVersionAdoption(
            package_version=stat.package_version,
            event_count=stat.total_events,
            session_count=stat.total_sessions,
            event_percentage=round(event_percentage, 2),
            session_percentage=round(session_percentage, 2),
            is_latest_version=None  # We don't track this in raw data anymore
        ))
    
    return result


@router.get("/debug/events")
async def debug_events(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_authentication)
):
    """Debug endpoint to check raw analytics events."""
    # Get user's API keys
    api_keys_query = select(APIKey).filter(APIKey.user_id == user_id)
    api_keys_result = await db.execute(api_keys_query)
    api_keys = api_keys_result.scalars().all()
    
    if not api_keys:
        return {"message": "No API keys found", "events": []}
    
    api_key_values = [key.key for key in api_keys]
    
    # Get recent events (last 100)
    events_query = select(AnalyticsEvent).filter(
        AnalyticsEvent.api_key.in_(api_key_values)
    ).order_by(desc(AnalyticsEvent.received_at)).limit(100)
    
    events_result = await db.execute(events_query)
    events = events_result.scalars().all()
    
    logger.info(f"Debug: Found {len(events)} events for user {user_id}")
    
    return {
        "api_keys": [{"key": key.key, "package": key.package_name} for key in api_keys],
        "total_events": len(events),
        "events": [
            {
                "id": str(event.id),
                "api_key": event.api_key,
                "package_name": event.package_name,
                "event_timestamp": event.event_timestamp.isoformat(),
                "received_at": event.received_at.isoformat(),
                "python_version": event.python_version,
                "os_type": event.os_type
            } for event in events[:10]  # Only show first 10 for brevity
        ]
    }
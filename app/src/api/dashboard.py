"""
Dashboard API endpoints for analytics data.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import aliased

from src.core.database import get_db
from src.core.auth import get_current_user_id, require_authentication
from src.models.api_key import APIKey
from src.models.analytics_aggregates import (
    DailyPackageStats, 
    PythonVersionStats, 
    OperatingSystemStats, 
    PackageVersionStats
)
from src.schemas.dashboard import (
    PackageOverview,
    TimeSeriesData,
    PythonVersionDistribution,
    OSDistribution,
    PackageVersionAdoption,
    DashboardFilters
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


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
    
    if not api_keys:
        return []
    
    api_key_values = [key.key for key in api_keys]
    
    # Get last 30 days of data
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Aggregate stats per package
    overview_data = []
    
    for api_key in api_keys:
        # Get total events and sessions for this package in last 30 days
        stats_query = select(
            func.sum(DailyPackageStats.total_events).label('total_events'),
            func.sum(DailyPackageStats.unique_sessions).label('total_sessions'),
            func.avg(DailyPackageStats.total_events).label('avg_daily_events'),
            func.count(DailyPackageStats.date).label('active_days')
        ).filter(
            and_(
                DailyPackageStats.api_key == api_key.key,
                DailyPackageStats.date >= start_date,
                DailyPackageStats.date <= end_date
            )
        )
        
        stats_result = await db.execute(stats_query)
        stats = stats_result.first()
        
        # Get Python version count
        python_versions_query = select(
            func.count(func.distinct(PythonVersionStats.python_version))
        ).filter(
            and_(
                PythonVersionStats.api_key == api_key.key,
                PythonVersionStats.date >= start_date
            )
        )
        python_versions_result = await db.execute(python_versions_query)
        python_version_count = python_versions_result.scalar() or 0
        
        # Get OS count
        os_query = select(
            func.count(func.distinct(OperatingSystemStats.os_type))
        ).filter(
            and_(
                OperatingSystemStats.api_key == api_key.key,
                OperatingSystemStats.date >= start_date
            )
        )
        os_result = await db.execute(os_query)
        os_count = os_result.scalar() or 0
        
        overview_data.append(PackageOverview(
            package_name=api_key.package_name,
            api_key=api_key.key,
            total_events=int(stats.total_events or 0),
            total_sessions=int(stats.total_sessions or 0),
            avg_daily_events=float(stats.avg_daily_events or 0),
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
    
    # Get daily aggregated data
    daily_stats_query = select(
        DailyPackageStats.date,
        DailyPackageStats.package_name,
        func.sum(DailyPackageStats.total_events).label('total_events'),
        func.sum(DailyPackageStats.unique_sessions).label('total_sessions')
    ).filter(
        and_(
            DailyPackageStats.api_key.in_(api_key_values),
            DailyPackageStats.date >= start_date,
            DailyPackageStats.date <= end_date
        )
    ).group_by(
        DailyPackageStats.date,
        DailyPackageStats.package_name
    ).order_by(DailyPackageStats.date)
    
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
    
    # Get user's API keys
    api_keys_query = select(APIKey).filter(APIKey.user_id == user_id)
    if package_name:
        api_keys_query = api_keys_query.filter(APIKey.package_name == package_name)
    
    api_keys_result = await db.execute(api_keys_query)
    api_keys = api_keys_result.scalars().all()
    
    if not api_keys:
        return []
    
    api_key_values = [key.key for key in api_keys]
    
    # Aggregate Python version stats
    python_stats_query = select(
        PythonVersionStats.python_version,
        func.sum(PythonVersionStats.event_count).label('total_events'),
        func.sum(PythonVersionStats.unique_sessions).label('total_sessions')
    ).filter(
        and_(
            PythonVersionStats.api_key.in_(api_key_values),
            PythonVersionStats.date >= start_date,
            PythonVersionStats.date <= end_date
        )
    ).group_by(PythonVersionStats.python_version).order_by(desc('total_events'))
    
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
    
    # Get user's API keys
    api_keys_query = select(APIKey).filter(APIKey.user_id == user_id)
    if package_name:
        api_keys_query = api_keys_query.filter(APIKey.package_name == package_name)
    
    api_keys_result = await db.execute(api_keys_query)
    api_keys = api_keys_result.scalars().all()
    
    if not api_keys:
        return []
    
    api_key_values = [key.key for key in api_keys]
    
    # Aggregate OS stats
    os_stats_query = select(
        OperatingSystemStats.os_type,
        func.sum(OperatingSystemStats.event_count).label('total_events'),
        func.sum(OperatingSystemStats.unique_sessions).label('total_sessions')
    ).filter(
        and_(
            OperatingSystemStats.api_key.in_(api_key_values),
            OperatingSystemStats.date >= start_date,
            OperatingSystemStats.date <= end_date
        )
    ).group_by(OperatingSystemStats.os_type).order_by(desc('total_events'))
    
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
    
    # Get package version stats
    version_stats_query = select(
        PackageVersionStats.package_version,
        func.sum(PackageVersionStats.event_count).label('total_events'),
        func.sum(PackageVersionStats.unique_sessions).label('total_sessions'),
        func.max(PackageVersionStats.is_latest_version).label('is_latest')
    ).filter(
        and_(
            PackageVersionStats.api_key == api_key.key,
            PackageVersionStats.date >= start_date,
            PackageVersionStats.date <= end_date
        )
    ).group_by(PackageVersionStats.package_version).order_by(desc('total_events'))
    
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
            is_latest_version=bool(stat.is_latest) if stat.is_latest is not None else None
        ))
    
    return result
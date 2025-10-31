"""
Refactored Dashboard API endpoints using the new architecture with services and repositories.
"""

from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
import logging

from src.core.auth import require_authentication
from src.core.service_dependencies import get_analytics_service
from src.services.analytics_service import AnalyticsService
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
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


@router.get("/overview")
async def get_dashboard_overview(
    package_name: Optional[str] = Query(None, description="Filter by package name"),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> List[PackageOverview]:
    """
    Get overview statistics for all user's packages or a specific package.
    """
    logger.info(f"Getting dashboard overview for user {user_id}, package filter: {package_name}")
    return await analytics_service.get_package_overview(user_id, package_name)


@router.get("/timeseries")
async def get_timeseries_data(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> TimeSeriesData:
    """
    Get time-series data for package usage over time.
    """
    logger.info(f"Getting timeseries data for user {user_id}, package: {package_name}")
    return await analytics_service.get_timeseries_data(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/python-versions")
async def get_python_version_distribution(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> List[PythonVersionDistribution]:
    """
    Get Python version distribution for packages.
    """
    logger.info(f"Getting Python version distribution for user {user_id}")
    return await analytics_service.get_python_version_distribution(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/operating-systems")
async def get_os_distribution(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> List[OSDistribution]:
    """
    Get operating system distribution for packages.
    """
    logger.info(f"Getting OS distribution for user {user_id}")
    return await analytics_service.get_os_distribution(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/package-versions")
async def get_package_version_adoption(
    package_name: str = Query(..., description="Package name to analyze"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> List[PackageVersionAdoption]:
    """
    Get package version adoption statistics.
    """
    logger.info(f"Getting package version adoption for user {user_id}, package: {package_name}")
    return await analytics_service.get_package_version_adoption(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )


# Unique User Tracking Endpoints

@router.get("/unique-users")
async def get_unique_users_overview(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> UniqueUsersOverview:
    """
    Get overview of unique users with DAU/WAU/MAU metrics.
    """
    logger.info(f"Getting unique users overview for user {user_id}, package: {package_name}")
    return await analytics_service.get_unique_users_overview(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/active-users")
async def get_active_users_timeseries(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> ActiveUsersTimeSeries:
    """
    Get time series data for active users (DAU/WAU/MAU over time).
    """
    logger.info(f"Getting active users timeseries for user {user_id}")
    return await analytics_service.get_active_users_timeseries(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/user-retention")
async def get_user_retention_metrics(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> UserRetentionMetrics:
    """
    Get user retention and engagement metrics.
    """
    logger.info(f"Getting user retention metrics for user {user_id}")
    return await analytics_service.get_user_retention_metrics(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/unique-users/by-os")
async def get_unique_users_by_os(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> List[UniqueUsersByDimension]:
    """
    Get unique users broken down by operating system.
    """
    logger.info(f"Getting unique users by OS for user {user_id}")
    return await analytics_service.get_unique_users_by_os(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/unique-users/by-python-version")
async def get_unique_users_by_python_version(
    package_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: int = Depends(require_authentication),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> List[UniqueUsersByDimension]:
    """
    Get unique users broken down by Python version.
    """
    logger.info(f"Getting unique users by Python version for user {user_id}")
    return await analytics_service.get_unique_users_by_python_version(
        user_id=user_id,
        package_name=package_name,
        start_date=start_date,
        end_date=end_date
    )
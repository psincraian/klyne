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
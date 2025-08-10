"""
Pydantic schemas for dashboard API responses.
"""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PackageOverview(BaseModel):
    """Overview statistics for a package."""

    package_name: str
    api_key: str
    total_events: int = Field(ge=0)
    total_sessions: int = Field(ge=0)
    avg_daily_events: float = Field(ge=0)
    active_days: int = Field(ge=0)
    python_versions_count: int = Field(ge=0)
    operating_systems_count: int = Field(ge=0)
    date_range_start: date
    date_range_end: date


class TimeSeriesData(BaseModel):
    """Time series data for charts."""

    dates: List[str]  # ISO date strings
    events: List[int]
    sessions: List[int]
    packages: List[str]  # List of package names included
    package_data: Optional[Dict[str, Any]] = None  # Detailed package breakdown


class PythonVersionDistribution(BaseModel):
    """Python version usage distribution."""

    python_version: str
    event_count: int = Field(ge=0)
    session_count: int = Field(ge=0)
    event_percentage: float = Field(ge=0, le=100)
    session_percentage: float = Field(ge=0, le=100)


class OSDistribution(BaseModel):
    """Operating system usage distribution."""

    os_type: str
    event_count: int = Field(ge=0)
    session_count: int = Field(ge=0)
    event_percentage: float = Field(ge=0, le=100)
    session_percentage: float = Field(ge=0, le=100)


class PackageVersionAdoption(BaseModel):
    """Package version adoption statistics."""

    package_version: str
    event_count: int = Field(ge=0)
    session_count: int = Field(ge=0)
    event_percentage: float = Field(ge=0, le=100)
    session_percentage: float = Field(ge=0, le=100)
    is_latest_version: Optional[bool] = None


class DashboardFilters(BaseModel):
    """Filters for dashboard data."""

    package_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    python_version: Optional[str] = None
    os_type: Optional[str] = None


class DashboardSummary(BaseModel):
    """Summary statistics for the entire dashboard."""

    total_packages: int = Field(ge=0)
    total_events: int = Field(ge=0)
    total_sessions: int = Field(ge=0)
    date_range_days: int = Field(ge=0)
    most_active_package: Optional[str] = None
    most_popular_python_version: Optional[str] = None
    most_popular_os: Optional[str] = None

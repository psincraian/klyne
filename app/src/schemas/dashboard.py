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
    total_unique_users: int = Field(ge=0, description="Total unique users in the date range")
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
    unique_users: List[int]  # Unique users per date
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


class UniqueUsersOverview(BaseModel):
    """Overview of unique users for a package."""

    package_name: str
    total_unique_users: int = Field(ge=0, description="Total unique users (all time)")
    daily_active_users: int = Field(ge=0, description="Unique users in last 24 hours")
    weekly_active_users: int = Field(ge=0, description="Unique users in last 7 days")
    monthly_active_users: int = Field(ge=0, description="Unique users in last 30 days")
    new_users_today: int = Field(ge=0, description="New unique users today")
    new_users_this_week: int = Field(ge=0, description="New unique users this week")
    new_users_this_month: int = Field(ge=0, description="New unique users this month")
    growth_rate_daily: Optional[float] = Field(None, description="Daily growth rate (%)")
    growth_rate_weekly: Optional[float] = Field(None, description="Weekly growth rate (%)")
    growth_rate_monthly: Optional[float] = Field(None, description="Monthly growth rate (%)")
    date_range_start: date
    date_range_end: date


class ActiveUsersTimeSeries(BaseModel):
    """Time series data for active users."""

    dates: List[str]  # ISO date strings
    daily_active_users: List[int]
    weekly_active_users: List[int]
    monthly_active_users: List[int]
    new_users: List[int]  # New users for each date
    returning_users: List[int]  # Returning users for each date


class UserRetentionMetrics(BaseModel):
    """User retention and engagement metrics."""

    total_users: int = Field(ge=0)
    new_users: int = Field(ge=0, description="Users in their first day/week/month")
    returning_users: int = Field(ge=0, description="Users who returned after first use")
    retention_rate: float = Field(ge=0, le=100, description="Percentage of returning users")
    avg_sessions_per_user: float = Field(ge=0, description="Average sessions per unique user")
    single_session_users: int = Field(ge=0, description="Users with only one session")
    multi_session_users: int = Field(ge=0, description="Users with multiple sessions")
    power_users: int = Field(ge=0, description="Users with 10+ sessions")


class UniqueUsersByDimension(BaseModel):
    """Unique users broken down by a dimension (OS, Python version, etc.)."""

    dimension_name: str  # e.g., "Linux", "3.11", etc.
    unique_users: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)
    avg_sessions_per_user: float = Field(ge=0)


class CustomEventType(BaseModel):
    """Custom event type with count."""

    event_type: str = Field(description="Name of the custom event (e.g., 'user_login', 'feature_used')")
    total_count: int = Field(ge=0, description="Total number of times this event was tracked")


class CustomEventTimeSeriesPoint(BaseModel):
    """Single data point in custom event time series."""

    date: str = Field(description="ISO date string")
    event_type: str = Field(description="Event type name")
    count: int = Field(ge=0, description="Number of events on this date")


class CustomEventTimeSeries(BaseModel):
    """Time series data for custom events."""

    dates: List[str] = Field(description="List of ISO date strings")
    event_types: List[str] = Field(description="List of event types included")
    series_data: Dict[str, List[int]] = Field(description="Event counts by type, keyed by event_type")


class CustomEventProperty(BaseModel):
    """Sample property data for a custom event."""

    properties: Dict[str, Any] = Field(description="The extra_data JSON for this event")
    timestamp: str = Field(description="ISO timestamp when event occurred")


class CustomEventDetails(BaseModel):
    """Detailed view of a specific custom event type."""

    event_type: str = Field(description="Name of the custom event")
    total_count: int = Field(ge=0, description="Total occurrences in date range")
    sample_properties: List[CustomEventProperty] = Field(description="Recent examples of event properties")

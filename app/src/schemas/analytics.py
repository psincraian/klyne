from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID


class AnalyticsEventCreate(BaseModel):
    """Schema for creating a new analytics event."""
    
    # Required fields
    api_key: str = Field(..., description="API key for the package")
    session_id: str = Field(..., description="Unique session identifier")
    package_name: str = Field(..., min_length=1, max_length=100, description="Package name")
    package_version: str = Field(..., min_length=1, max_length=50, description="Package version")
    python_version: str = Field(..., description="Python version (e.g., '3.11.5')")
    os_type: str = Field(..., description="Operating system type")
    event_timestamp: datetime = Field(..., description="When the event occurred")
    
    # Optional environment fields
    python_implementation: Optional[str] = Field(None, max_length=50, description="Python implementation")
    os_version: Optional[str] = Field(None, max_length=100, description="OS version")
    os_release: Optional[str] = Field(None, max_length=100, description="OS release name")
    architecture: Optional[str] = Field(None, max_length=20, description="CPU architecture")
    
    # Optional installation context
    installation_method: Optional[str] = Field(None, max_length=50, description="Installation method")
    virtual_env: Optional[bool] = Field(False, description="Running in virtual environment")
    virtual_env_type: Optional[str] = Field(None, max_length=50, description="Virtual environment type")
    
    # Optional hardware data
    cpu_count: Optional[int] = Field(None, ge=1, le=1000, description="CPU core count")
    total_memory_gb: Optional[int] = Field(None, ge=1, le=1000, description="Total memory in GB")
    
    # Optional usage context
    entry_point: Optional[str] = Field(None, max_length=200, description="Entry point used")
    
    # Extensible metadata
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator('python_version')
    def validate_python_version(cls, v):
        """Validate Python version format."""
        if not v:
            raise ValueError('Python version is required')
        # Basic format validation (e.g., "3.11.5" or "3.11")
        parts = v.split('.')
        if len(parts) < 2 or not all(part.isdigit() for part in parts):
            raise ValueError('Invalid Python version format')
        return v

    @validator('os_type')
    def validate_os_type(cls, v):
        """Validate OS type."""
        valid_os_types = ['Linux', 'Windows', 'Darwin', 'FreeBSD', 'OpenBSD', 'Other']
        if v not in valid_os_types:
            return 'Other'  # Default to 'Other' for unknown OS types
        return v

    @validator('session_id')
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if not v:
            raise ValueError('Session ID is required')
        # Try to parse as UUID to ensure it's a valid format
        try:
            UUID(v)
        except ValueError:
            raise ValueError('Session ID must be a valid UUID')
        return v


    class Config:
        # Allow extra fields for forward compatibility
        extra = "ignore"
        # Example data for documentation
        schema_extra = {
            "example": {
                "api_key": "klyne_abc123...",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "package_name": "requests",
                "package_version": "2.31.0",
                "python_version": "3.11.5",
                "python_implementation": "CPython",
                "os_type": "Linux",
                "os_version": "5.15.0",
                "os_release": "Ubuntu 22.04",
                "architecture": "x86_64",
                "installation_method": "pip",
                "virtual_env": True,
                "virtual_env_type": "venv",
                "cpu_count": 8,
                "total_memory_gb": 16,
                "entry_point": "requests.get",
                "event_timestamp": "2024-01-15T10:30:00Z",
                "extra_data": {
                    "user_agent": "requests/2.31.0",
                    "custom_field": "value"
                }
            }
        }


class AnalyticsEventResponse(BaseModel):
    """Schema for analytics event responses."""
    
    id: UUID
    api_key: str
    session_id: UUID
    package_name: str
    package_version: str
    python_version: str
    os_type: str
    event_timestamp: datetime
    received_at: datetime
    processed: bool

    class Config:
        from_attributes = True


class AnalyticsEventBatch(BaseModel):
    """Schema for batch analytics event submission."""
    
    events: list[AnalyticsEventCreate] = Field(..., min_items=1, max_items=100, 
                                              description="List of analytics events")
    
    class Config:
        schema_extra = {
            "example": {
                "events": [
                    {
                        "api_key": "klyne_abc123...",
                        "session_id": "550e8400-e29b-41d4-a716-446655440000",
                        "package_name": "requests",
                        "package_version": "2.31.0",
                        "python_version": "3.11.5",
                        "os_type": "Linux",
                        "event_timestamp": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        }


class DailyStatsResponse(BaseModel):
    """Schema for daily package statistics."""
    
    package_name: str
    date: str  # ISO date format
    total_events: int
    unique_sessions: int
    unique_users_estimate: int

    class Config:
        from_attributes = True


class PythonVersionDistribution(BaseModel):
    """Schema for Python version distribution data."""
    
    python_version: str
    event_count: int
    unique_sessions: int
    percentage: float

    class Config:
        from_attributes = True


class OperatingSystemDistribution(BaseModel):
    """Schema for OS distribution data."""
    
    os_type: str
    os_version: Optional[str] = None
    event_count: int
    unique_sessions: int
    percentage: float

    class Config:
        from_attributes = True
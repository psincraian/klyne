from pydantic import BaseModel, Field, validator, model_validator
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
import json
import re


class AnalyticsEventCreate(BaseModel):
    """Schema for creating a new analytics event."""

    # Required fields
    session_id: str = Field(..., description="Unique session identifier")
    package_name: str = Field(
        ..., min_length=1, max_length=100, description="Package name"
    )
    package_version: str = Field(
        ..., min_length=1, max_length=50, description="Package version"
    )
    python_version: str = Field(..., description="Python version (e.g., '3.11.5')")
    os_type: str = Field(..., description="Operating system type")
    event_timestamp: datetime = Field(..., description="When the event occurred")

    # Unique user tracking fields (optional, for pseudonymous analytics)
    installation_id: Optional[str] = Field(
        None, description="Persistent installation UUID for unique user tracking"
    )
    fingerprint_hash: Optional[str] = Field(
        None, max_length=64, description="Hashed hardware fingerprint for fallback identification"
    )
    user_identifier: Optional[str] = Field(
        None, max_length=100, description="Coalesced user identifier (installation_id or fingerprint_hash)"
    )

    # Optional environment fields
    python_implementation: Optional[str] = Field(
        None, max_length=50, description="Python implementation"
    )
    os_version: Optional[str] = Field(None, max_length=100, description="OS version")
    os_release: Optional[str] = Field(
        None, max_length=100, description="OS release name"
    )
    architecture: Optional[str] = Field(
        None, max_length=20, description="CPU architecture"
    )

    # Optional installation context
    installation_method: Optional[str] = Field(
        None, max_length=50, description="Installation method"
    )
    virtual_env: Optional[bool] = Field(
        False, description="Running in virtual environment"
    )
    virtual_env_type: Optional[str] = Field(
        None, max_length=50, description="Virtual environment type"
    )

    # Optional hardware data
    cpu_count: Optional[int] = Field(None, ge=1, le=1000, description="CPU core count")
    total_memory_gb: Optional[int] = Field(
        None, ge=1, le=1000, description="Total memory in GB"
    )

    # Optional usage context
    entry_point: Optional[str] = Field(
        None, max_length=200, description="Entry point used"
    )

    # Extensible metadata
    extra_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata"
    )

    @validator("python_version")
    def validate_python_version(cls, v):
        """Validate Python version format."""
        if not v:
            raise ValueError("Python version is required")
        # Basic format validation (e.g., "3.11.5" or "3.11")
        parts = v.split(".")
        if len(parts) < 2 or not all(part.isdigit() for part in parts):
            raise ValueError("Invalid Python version format")
        return v

    @validator("os_type")
    def validate_os_type(cls, v):
        """Validate OS type."""
        valid_os_types = ["Linux", "Windows", "Darwin", "FreeBSD", "OpenBSD", "Other"]
        if v not in valid_os_types:
            return "Other"  # Default to 'Other' for unknown OS types
        return v

    @validator("session_id")
    def validate_session_id(cls, v):
        """Validate session ID format."""
        if not v:
            raise ValueError("Session ID is required")
        # Try to parse as UUID to ensure it's a valid format
        try:
            UUID(v)
        except ValueError:
            raise ValueError("Session ID must be a valid UUID")
        return v

    @model_validator(mode='before')
    @classmethod
    def capture_extra_fields(cls, values):
        """
        Capture any extra fields at the root level and merge them into extra_data.
        This allows custom properties to be sent at the root level by the SDK
        while storing them in the extra_data JSON column in the database.

        Security validations:
        - Maximum 50 custom properties
        - Property names must be alphanumeric with underscores, max 64 chars
        - Total JSON size limit of 10KB
        - Maximum nesting depth of 5 levels
        """
        if not isinstance(values, dict):
            return values

        # Get the defined field names
        defined_fields = {
            'session_id', 'package_name', 'package_version', 'python_version',
            'os_type', 'event_timestamp', 'installation_id', 'fingerprint_hash',
            'user_identifier', 'python_implementation', 'os_version', 'os_release',
            'architecture', 'installation_method', 'virtual_env', 'virtual_env_type',
            'cpu_count', 'total_memory_gb', 'entry_point', 'extra_data'
        }

        # Find extra fields (custom properties)
        extra_fields = {k: v for k, v in values.items() if k not in defined_fields}

        # If there are extra fields, validate and merge them into extra_data
        if extra_fields:
            # Validate number of custom properties (prevent excessive properties)
            MAX_CUSTOM_PROPERTIES = 50
            if len(extra_fields) > MAX_CUSTOM_PROPERTIES:
                raise ValueError(f"Too many custom properties. Maximum {MAX_CUSTOM_PROPERTIES} allowed, got {len(extra_fields)}.")

            # Validate property names (alphanumeric + underscore only, max length)
            PROPERTY_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{1,64}$')
            invalid_keys = [k for k in extra_fields.keys() if not PROPERTY_NAME_PATTERN.match(str(k))]
            if invalid_keys:
                raise ValueError(
                    f"Invalid property names: {invalid_keys}. "
                    "Property names must be alphanumeric with underscores, max 64 characters."
                )

            # Validate serialized size (prevent JSON bombs)
            MAX_JSON_SIZE_BYTES = 10 * 1024  # 10KB limit for custom properties
            try:
                serialized = json.dumps(extra_fields)
                if len(serialized) > MAX_JSON_SIZE_BYTES:
                    raise ValueError(
                        f"Custom properties too large: {len(serialized)} bytes. "
                        f"Maximum {MAX_JSON_SIZE_BYTES} bytes allowed."
                    )
            except (TypeError, ValueError) as e:
                if "too large" in str(e):
                    raise
                raise ValueError(f"Custom properties must be JSON-serializable: {str(e)}")

            # Validate JSON depth (prevent deeply nested objects)
            def get_depth(obj, current_depth=0):
                if current_depth > 5:  # Max 5 levels deep
                    raise ValueError("Custom properties too deeply nested. Maximum 5 levels allowed.")
                if isinstance(obj, dict):
                    if not obj:  # Empty dict
                        return current_depth
                    return max((get_depth(v, current_depth + 1) for v in obj.values()), default=current_depth)
                elif isinstance(obj, list):
                    if not obj:  # Empty list
                        return current_depth
                    return max((get_depth(item, current_depth + 1) for item in obj), default=current_depth)
                return current_depth

            try:
                get_depth(extra_fields)
            except ValueError:
                raise

            # Merge validated extra fields into extra_data
            existing_extra_data = values.get('extra_data', {}) or {}
            merged_extra_data = {**existing_extra_data, **extra_fields}
            values['extra_data'] = merged_extra_data

            # Remove extra fields from root level to avoid Pydantic warnings
            for key in extra_fields:
                values.pop(key, None)

        return values

    class Config:
        # Allow extra fields for forward compatibility
        extra = "allow"
        # Example data for documentation
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "installation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "fingerprint_hash": "a3c2e1b9f8d7c6e5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1",
                "user_identifier": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
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
                    "custom_field": "value",
                },
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

    class Config:
        from_attributes = True


class AnalyticsEventBatch(BaseModel):
    """Schema for batch analytics event submission."""

    events: list[AnalyticsEventCreate] = Field(
        ..., description="List of analytics events"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "session_id": "550e8400-e29b-41d4-a716-446655440000",
                        "package_name": "requests",
                        "package_version": "2.31.0",
                        "python_version": "3.11.5",
                        "os_type": "Linux",
                        "event_timestamp": "2024-01-15T10:30:00Z",
                    }
                ]
            }
        }

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from src.models import Base
import uuid


class AnalyticsEvent(Base):
    """
    Raw analytics events collected from package usage.
    Each event represents one package startup/initialization.
    """
    __tablename__ = "analytics_events"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    api_key = Column(String, nullable=False, index=True)  # Links to API key
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Unique per package run
    
    # Package information
    package_name = Column(String, nullable=False, index=True)
    package_version = Column(String, nullable=False, index=True)
    
    # Environment information
    python_version = Column(String, nullable=False, index=True)  # e.g., "3.11.5"
    python_implementation = Column(String, nullable=True)  # CPython, PyPy, etc.
    
    # Operating system
    os_type = Column(String, nullable=False, index=True)  # Linux, Windows, Darwin
    os_version = Column(String, nullable=True)  # Specific OS version
    os_release = Column(String, nullable=True)  # Ubuntu 22.04, Windows 11, etc.
    architecture = Column(String, nullable=True, index=True)  # x86_64, arm64, etc.
    
    # Installation context
    installation_method = Column(String, nullable=True)  # pip, conda, poetry, etc.
    virtual_env = Column(Boolean, default=False)  # Running in virtual environment
    virtual_env_type = Column(String, nullable=True)  # venv, conda, pipenv, etc.
    
    # Hardware (optional)
    cpu_count = Column(Integer, nullable=True)
    total_memory_gb = Column(Integer, nullable=True)  # Rounded to GB for privacy
    
    # Usage context
    entry_point = Column(String, nullable=True)  # How the package was invoked
    
    # Extensible metadata
    extra_data = Column(JSON, nullable=True)  # Additional structured data
    
    # Timestamps
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Indexes for common queries
    __table_args__ = (
        # Performance indexes for dashboard queries
        Index('idx_analytics_package_date', 'package_name', 'event_timestamp'),
        Index('idx_analytics_api_key_date', 'api_key', 'event_timestamp'),
        Index('idx_analytics_python_version', 'package_name', 'python_version'),
        Index('idx_analytics_os_type', 'package_name', 'os_type'),
        
        # Composite indexes for aggregation queries
        Index('idx_analytics_aggregation', 'package_name', 'event_timestamp', 'python_version', 'os_type'),
    )
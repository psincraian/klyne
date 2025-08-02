from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Date, Index, UniqueConstraint
from sqlalchemy.sql import func
from src.models import Base


class DailyPackageStats(Base):
    """
    Daily aggregated statistics per package.
    Pre-computed for fast dashboard queries.
    """
    __tablename__ = "daily_package_stats"

    id = Column(Integer, primary_key=True, index=True)
    
    # Grouping dimensions
    package_name = Column(String, nullable=False, index=True)
    api_key = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Aggregated metrics
    total_events = Column(BigInteger, nullable=False, default=0)
    unique_sessions = Column(BigInteger, nullable=False, default=0)
    unique_users_estimate = Column(BigInteger, nullable=False, default=0)  # Based on session patterns
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('package_name', 'api_key', 'date', name='uq_daily_package_stats'),
        Index('idx_daily_stats_package_date', 'package_name', 'date'),
        Index('idx_daily_stats_api_key_date', 'api_key', 'date'),
    )


class PythonVersionStats(Base):
    """
    Python version distribution per package over time.
    """
    __tablename__ = "python_version_stats"

    id = Column(Integer, primary_key=True, index=True)
    
    # Grouping dimensions
    package_name = Column(String, nullable=False, index=True)
    api_key = Column(String, nullable=False, index=True)
    python_version = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Metrics
    event_count = Column(BigInteger, nullable=False, default=0)
    unique_sessions = Column(BigInteger, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('package_name', 'api_key', 'python_version', 'date', 
                        name='uq_python_version_stats'),
        Index('idx_python_stats_package_date', 'package_name', 'date'),
    )


class OperatingSystemStats(Base):
    """
    Operating system distribution per package over time.
    """
    __tablename__ = "operating_system_stats"

    id = Column(Integer, primary_key=True, index=True)
    
    # Grouping dimensions  
    package_name = Column(String, nullable=False, index=True)
    api_key = Column(String, nullable=False, index=True)
    os_type = Column(String, nullable=False, index=True)
    os_version = Column(String, nullable=True)  # More granular OS version
    date = Column(Date, nullable=False, index=True)
    
    # Metrics
    event_count = Column(BigInteger, nullable=False, default=0)
    unique_sessions = Column(BigInteger, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('package_name', 'api_key', 'os_type', 'os_version', 'date',
                        name='uq_os_stats'),
        Index('idx_os_stats_package_date', 'package_name', 'date'),
    )



class PackageVersionStats(Base):
    """
    Package version adoption tracking over time.
    """
    __tablename__ = "package_version_stats"

    id = Column(Integer, primary_key=True, index=True)
    
    # Grouping dimensions
    package_name = Column(String, nullable=False, index=True)
    api_key = Column(String, nullable=False, index=True)
    package_version = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Metrics
    event_count = Column(BigInteger, nullable=False, default=0)
    unique_sessions = Column(BigInteger, nullable=False, default=0)
    
    # Version metadata
    is_latest_version = Column(Integer, nullable=True)  # 1 if latest, 0 if not, null if unknown
    version_age_days = Column(Integer, nullable=True)  # Days since version release
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('package_name', 'api_key', 'package_version', 'date',
                        name='uq_package_version_stats'),
        Index('idx_version_stats_package_date', 'package_name', 'date'),
        Index('idx_version_stats_latest', 'package_name', 'is_latest_version', 'date'),
    )
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from src.models.analytics_event import AnalyticsEvent
from src.schemas.analytics import AnalyticsEventCreate


class TestAnalyticsModels:
    
    @pytest_asyncio.fixture
    async def sample_event_data(self):
        """Sample analytics event data."""
        return {
            "api_key": "klyne_test123",
            "session_id": str(uuid4()),
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
            "event_timestamp": datetime.now(timezone.utc),
            "extra_data": {"custom": "value"}
        }
    
    @pytest_asyncio.fixture
    async def test_analytics_event_creation(self, sample_event_data, async_session):
        """Test creating an analytics event."""
        event = AnalyticsEvent(**sample_event_data)
        async_session.add(event)
        await async_session.commit()
        await async_session.refresh(event)
        
        # Verify event was created
        assert event.id is not None
        assert event.package_name == "requests"
        assert event.package_version == "2.31.0"
        assert event.python_version == "3.11.5"
        assert event.os_type == "Linux"
        assert event.virtual_env is True
        assert event.extra_data == {"custom": "value"}
        assert event.received_at is not None
        assert event.processed is False
        
        return event
    
    @pytest_asyncio.fixture
    async def test_analytics_event_querying(self, test_analytics_event_creation, async_session):
        """Test querying analytics events."""
        event = test_analytics_event_creation
        
        # Query by package name
        result = await async_session.execute(
            select(AnalyticsEvent).filter(AnalyticsEvent.package_name == "requests")
        )
        events = result.scalars().all()
        
        assert len(events) >= 1
        found_event = next((e for e in events if e.id == event.id), None)
        assert found_event is not None
        assert found_event.package_name == "requests"
        
        # Query by Python version
        result = await async_session.execute(
            select(AnalyticsEvent).filter(AnalyticsEvent.python_version == "3.11.5")
        )
        events = result.scalars().all()
        assert len(events) >= 1

    def test_analytics_event_schema_validation(self):
        """Test analytics event schema validation."""
        # Valid data
        valid_data = {
            "api_key": "klyne_test123",
            "session_id": str(uuid4()),
            "package_name": "requests",
            "package_version": "2.31.0",
            "python_version": "3.11.5",
            "os_type": "Linux",
            "event_timestamp": datetime.now(timezone.utc)
        }
        
        event = AnalyticsEventCreate(**valid_data)
        assert event.package_name == "requests"
        assert event.python_version == "3.11.5"
        assert event.os_type == "Linux"
        
        # Test validation errors
        with pytest.raises(ValueError, match="Python version is required"):
            AnalyticsEventCreate(**{**valid_data, "python_version": ""})
        
        with pytest.raises(ValueError, match="Invalid Python version format"):
            AnalyticsEventCreate(**{**valid_data, "python_version": "invalid"})
        
        with pytest.raises(ValueError, match="Session ID must be a valid UUID"):
            AnalyticsEventCreate(**{**valid_data, "session_id": "invalid-uuid"})
        
        # Test OS type normalization
        event_unknown_os = AnalyticsEventCreate(**{**valid_data, "os_type": "UnknownOS"})
        assert event_unknown_os.os_type == "Other"
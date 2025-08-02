import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4


class TestAnalyticsAPISimple:
    
    def test_analytics_health_endpoint_loads(self):
        """Test that analytics health endpoint can be imported."""
        from src.api.analytics import router
        assert router is not None
        
        # Check that the router has the expected endpoints
        paths = [route.path for route in router.routes]
        assert "/api/analytics/health" in paths
        assert "/api/analytics" in paths
        assert "/api/analytics/batch" in paths
    
    def test_api_auth_module_loads(self):
        """Test that API auth module loads correctly."""
        from src.core.api_auth import authenticate_analytics_request, get_api_key_from_token
        assert authenticate_analytics_request is not None
        assert get_api_key_from_token is not None
    
    def test_rate_limiter_module_loads(self):
        """Test that rate limiter module loads correctly."""
        from src.core.rate_limiter import check_rate_limit, rate_limiter
        assert check_rate_limit is not None
        assert rate_limiter is not None
    
    def test_analytics_schemas_load(self):
        """Test that analytics schemas load correctly."""
        from src.schemas.analytics import AnalyticsEventCreate, AnalyticsEventBatch
        
        # Test schema validation
        valid_data = {
            "api_key": "klyne_test123",
            "session_id": str(uuid4()),
            "package_name": "test-package",
            "package_version": "1.0.0",
            "python_version": "3.11.5",
            "os_type": "Linux",
            "event_timestamp": datetime.now(timezone.utc)
        }
        
        event = AnalyticsEventCreate(**valid_data)
        assert event.package_name == "test-package"
        assert event.python_version == "3.11.5"
        
        # Test batch schema
        batch = AnalyticsEventBatch(events=[valid_data])
        assert len(batch.events) == 1
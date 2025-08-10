import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from src.models.analytics_event import AnalyticsEvent
from src.models.api_key import APIKey
from src.models.user import User
from src.core.auth import get_password_hash


class TestAnalyticsAPI:
    
    @pytest_asyncio.fixture
    async def test_user_and_api_key(self, async_session):
        """Create a test user and API key."""
        # Create test user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        # Create test API key
        api_key = APIKey(
            package_name="test-package",
            key="klyne_test_key_123456789",
            user_id=user.id
        )
        async_session.add(api_key)
        await async_session.commit()
        await async_session.refresh(api_key)
        
        return user, api_key
    
    @pytest_asyncio.fixture
    async def sample_analytics_data(self):
        """Sample analytics event data."""
        return {
            "session_id": str(uuid4()),
            "package_name": "test-package",
            "package_version": "1.0.0",
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
            "entry_point": "test.main",
            "event_timestamp": datetime.now(timezone.utc).isoformat(),
            "extra_data": {"custom": "value"}
        }
    
    async def test_analytics_health_check(self, client):
        """Test analytics health check endpoint."""
        response = await client.get("/api/analytics/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "analytics"
        assert "timestamp" in data
    
    async def test_create_analytics_event_success(
        self, 
        client, 
        test_user_and_api_key, 
        sample_analytics_data,
        async_session
    ):
        """Test successful analytics event creation."""
        user, api_key = test_user_and_api_key
        
        headers = {"Authorization": f"Bearer {api_key.key}"}
        
        response = await client.post(
            "/api/analytics",
            json=sample_analytics_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "event_id" in data
        assert "received_at" in data
        assert data["message"] == "Analytics event recorded successfully"
        
        # Verify rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        # Verify event was created in database
        result = await async_session.execute(
            select(AnalyticsEvent).filter(
                AnalyticsEvent.package_name == "test-package"
            )
        )
        events = result.scalars().all()
        assert len(events) >= 1
        
        event = events[0]
        assert event.package_name == "test-package"
        assert event.package_version == "1.0.0"
        assert event.python_version == "3.11.5"
        assert event.os_type == "Linux"
        assert event.api_key == api_key.key
    
    async def test_create_analytics_event_no_auth(self, client, sample_analytics_data):
        """Test analytics event creation without authentication."""
        response = await client.post("/api/analytics", json=sample_analytics_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "API key required" in data["detail"]
    
    async def test_create_analytics_event_invalid_api_key(self, client, sample_analytics_data):
        """Test analytics event creation with invalid API key."""
        headers = {"Authorization": "Bearer invalid_key"}
        
        response = await client.post(
            "/api/analytics",
            json=sample_analytics_data,
            headers=headers
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid API key format" in data["detail"]
    
    async def test_create_analytics_event_wrong_package(
        self,
        client,
        test_user_and_api_key,
        sample_analytics_data
    ):
        """Test analytics event creation with wrong package name."""
        user, api_key = test_user_and_api_key
        
        # Modify data to use different package name
        wrong_package_data = {**sample_analytics_data, "package_name": "different-package"}
        headers = {"Authorization": f"Bearer {api_key.key}"}
        
        response = await client.post(
            "/api/analytics",
            json=wrong_package_data,
            headers=headers
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "not authorized for package" in data["detail"]
    
    async def test_create_analytics_batch_success(
        self,
        client,
        test_user_and_api_key,
        sample_analytics_data,
        async_session
    ):
        """Test successful batch analytics event creation."""
        user, api_key = test_user_and_api_key
        
        # Create batch with 3 events
        batch_data = {
            "events": [
                {**sample_analytics_data, "session_id": str(uuid4())},
                {**sample_analytics_data, "session_id": str(uuid4()), "python_version": "3.10.0"},
                {**sample_analytics_data, "session_id": str(uuid4()), "os_type": "Windows"}
            ]
        }
        
        headers = {"Authorization": f"Bearer {api_key.key}"}
        
        response = await client.post(
            "/api/analytics/batch",
            json=batch_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["created_count"] == 3
        assert data["failed_count"] == 0
        assert len(data["created_events"]) == 3
        assert data["failed_events"] is None
        
        # Verify events were created in database
        result = await async_session.execute(
            select(AnalyticsEvent).filter(
                AnalyticsEvent.package_name == "test-package"
            )
        )
        events = result.scalars().all()
        assert len(events) >= 3
    
    async def test_create_analytics_batch_too_large(
        self,
        client,
        test_user_and_api_key,
        sample_analytics_data
    ):
        """Test batch analytics with too many events."""
        user, api_key = test_user_and_api_key
        
        # Create batch with 101 events (over the limit)
        batch_data = {
            "events": [
                {**sample_analytics_data, "session_id": str(uuid4())}
                for _ in range(101)
            ]
        }
        
        headers = {"Authorization": f"Bearer {api_key.key}"}
        
        response = await client.post(
            "/api/analytics/batch",
            json=batch_data,
            headers=headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "cannot exceed 100 events" in data["detail"]
    
    async def test_create_analytics_batch_empty(
        self,
        client,
        test_user_and_api_key
    ):
        """Test batch analytics with empty events list."""
        user, api_key = test_user_and_api_key
        
        batch_data = {"events": []}
        headers = {"Authorization": f"Bearer {api_key.key}"}
        
        response = await client.post(
            "/api/analytics/batch",
            json=batch_data,
            headers=headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "cannot be empty" in data["detail"]
    
    async def test_analytics_event_validation_errors(
        self,
        client,
        test_user_and_api_key
    ):
        """Test analytics event validation errors."""
        user, api_key = test_user_and_api_key
        headers = {"Authorization": f"Bearer {api_key.key}"}
        
        # Test missing required fields
        invalid_data = {
            "package_name": "test-package",
            # Missing other required fields
        }
        
        response = await client.post(
            "/api/analytics",
            json=invalid_data,
            headers=headers
        )
        
        assert response.status_code == 422  # Validation error
        
        # Test invalid Python version
        invalid_python_data = {
            "session_id": str(uuid4()),
            "package_name": "test-package",
            "package_version": "1.0.0",
            "python_version": "invalid",
            "os_type": "Linux",
            "event_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = await client.post(
            "/api/analytics",
            json=invalid_python_data,
            headers=headers
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_rate_limiting_simulation(
        self,
        client,
        test_user_and_api_key,
        sample_analytics_data
    ):
        """Test that rate limiting headers are present (simulation)."""
        user, api_key = test_user_and_api_key
        headers = {"Authorization": f"Bearer {api_key.key}"}
        
        response = await client.post(
            "/api/analytics",
            json=sample_analytics_data,
            headers=headers
        )
        
        assert response.status_code == 200
        
        # Check rate limit headers are present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        # Verify header values are reasonable
        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        
        assert limit > 0
        assert remaining >= 0
        assert remaining <= limit
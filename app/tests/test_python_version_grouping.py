import pytest_asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.models.analytics_event import AnalyticsEvent
from src.models.api_key import APIKey
from src.models.user import User
from src.repositories.analytics_event_repository import AnalyticsEventRepository
from src.core.auth import get_password_hash


class TestPythonVersionGrouping:
    @pytest_asyncio.fixture
    async def test_user_and_api_key(self, async_session):
        """Create a test user and API key."""
        # Create test user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create test API key
        api_key = APIKey(
            package_name="test-package", key="klyne_test_key_123456789", user_id=user.id
        )
        async_session.add(api_key)
        await async_session.commit()
        await async_session.refresh(api_key)

        return user, api_key

    @pytest_asyncio.fixture
    async def sample_events_with_versions(self, async_session, test_user_and_api_key):
        """Create sample analytics events with different Python versions."""
        user, api_key = test_user_and_api_key
        now = datetime.now(timezone.utc)

        # Create events with various Python versions
        # 3.11.0, 3.11.1, 3.11.2 should group to 3.11
        # 3.12.0, 3.12.1 should group to 3.12
        # 3.13.0 should group to 3.13
        events_data = [
            # Python 3.11 events (3 events, 3 sessions)
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.11.0",
                "os_type": "Linux",
                "event_timestamp": now,
            },
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.11.1",
                "os_type": "Linux",
                "event_timestamp": now,
            },
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.11.2",
                "os_type": "Linux",
                "event_timestamp": now,
            },
            # Python 3.12 events (2 events, 2 sessions)
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.12.0",
                "os_type": "Linux",
                "event_timestamp": now,
            },
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.12.1",
                "os_type": "Windows",
                "event_timestamp": now,
            },
            # Python 3.13 events (1 event, 1 session)
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.13.0",
                "os_type": "macOS",
                "event_timestamp": now,
            },
        ]

        # Create events in database
        events = []
        for event_data in events_data:
            event = AnalyticsEvent(**event_data)
            async_session.add(event)
            events.append(event)

        await async_session.commit()

        return events, api_key

    async def test_python_version_distribution_groups_by_minor(
        self, async_session, sample_events_with_versions
    ):
        """Test that Python version distribution groups by minor version."""
        events, api_key = sample_events_with_versions

        # Create repository
        repo = AnalyticsEventRepository(async_session)

        # Get distribution
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc) + timedelta(days=1)

        distribution = await repo.get_python_version_distribution(
            api_keys=[api_key.key],
            start_date=start_date,
            end_date=end_date,
        )

        # Verify results
        assert len(distribution) == 3, "Should have 3 groups (3.11, 3.12, 3.13)"

        # Sort by Python version for easier testing
        distribution_sorted = sorted(distribution, key=lambda x: x["python_version"])

        # Check Python 3.11 group
        py_311 = distribution_sorted[0]
        assert py_311["python_version"] == "3.11"
        assert py_311["total_events"] == 3
        assert py_311["total_sessions"] == 3

        # Check Python 3.12 group
        py_312 = distribution_sorted[1]
        assert py_312["python_version"] == "3.12"
        assert py_312["total_events"] == 2
        assert py_312["total_sessions"] == 2

        # Check Python 3.13 group
        py_313 = distribution_sorted[2]
        assert py_313["python_version"] == "3.13"
        assert py_313["total_events"] == 1
        assert py_313["total_sessions"] == 1

    async def test_unique_python_versions_count_by_minor(
        self, async_session, sample_events_with_versions
    ):
        """Test that unique Python versions count groups by minor version."""
        events, api_key = sample_events_with_versions

        # Create repository
        repo = AnalyticsEventRepository(async_session)

        # Get unique versions count
        start_date = datetime.now(timezone.utc) - timedelta(days=1)

        count = await repo.get_unique_python_versions_count(
            api_key=api_key.key,
            start_date=start_date,
        )

        # Should count 3 unique minor versions: 3.11, 3.12, 3.13
        assert count == 3

    async def test_unique_users_by_python_version_groups_by_minor(
        self, async_session, test_user_and_api_key
    ):
        """Test that unique users by Python version groups by minor version."""
        user, api_key = test_user_and_api_key
        now = datetime.now(timezone.utc)

        # Create events with user identifiers and different Python versions
        events_data = [
            # User 1 on Python 3.11.0 and 3.11.1
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "user_identifier": "user1",
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.11.0",
                "os_type": "Linux",
                "event_timestamp": now,
            },
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "user_identifier": "user1",
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.11.1",
                "os_type": "Linux",
                "event_timestamp": now,
            },
            # User 2 on Python 3.12.0
            {
                "api_key": api_key.key,
                "session_id": uuid4(),
                "user_identifier": "user2",
                "package_name": "test-package",
                "package_version": "1.0.0",
                "python_version": "3.12.0",
                "os_type": "Windows",
                "event_timestamp": now,
            },
        ]

        # Create events in database
        for event_data in events_data:
            event = AnalyticsEvent(**event_data)
            async_session.add(event)

        await async_session.commit()

        # Create repository
        repo = AnalyticsEventRepository(async_session)

        # Get unique users by Python version
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc) + timedelta(days=1)

        users_by_version = await repo.get_unique_users_by_dimension(
            api_keys=[api_key.key],
            dimension_field="python_version",
            start_date=start_date,
            end_date=end_date,
        )

        # Verify results
        assert len(users_by_version) == 2, "Should have 2 groups (3.11, 3.12)"

        # Sort by dimension name for easier testing
        users_sorted = sorted(users_by_version, key=lambda x: x["dimension_name"])

        # Check Python 3.11 group (user1 should be counted once despite using 3.11.0 and 3.11.1)
        py_311_users = users_sorted[0]
        assert py_311_users["dimension_name"] == "3.11"
        assert py_311_users["unique_users"] == 1
        assert py_311_users["total_sessions"] == 2

        # Check Python 3.12 group
        py_312_users = users_sorted[1]
        assert py_312_users["dimension_name"] == "3.12"
        assert py_312_users["unique_users"] == 1
        assert py_312_users["total_sessions"] == 1

    async def test_python_version_already_minor(
        self, async_session, test_user_and_api_key
    ):
        """Test that versions already in minor format (e.g., '3.11') work correctly."""
        user, api_key = test_user_and_api_key
        now = datetime.now(timezone.utc)

        # Create event with version already in minor format
        event = AnalyticsEvent(
            api_key=api_key.key,
            session_id=uuid4(),
            package_name="test-package",
            package_version="1.0.0",
            python_version="3.11",
            os_type="Linux",
            event_timestamp=now,
        )
        async_session.add(event)
        await async_session.commit()

        # Create repository
        repo = AnalyticsEventRepository(async_session)

        # Get distribution
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc) + timedelta(days=1)

        distribution = await repo.get_python_version_distribution(
            api_keys=[api_key.key],
            start_date=start_date,
            end_date=end_date,
        )

        # Verify results
        assert len(distribution) == 1
        assert distribution[0]["python_version"] == "3.11"
        assert distribution[0]["total_events"] == 1

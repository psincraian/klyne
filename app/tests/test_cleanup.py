"""
Tests for free plan data cleanup functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select

from src.models.user import User
from src.models.api_key import APIKey
from src.models.analytics_event import AnalyticsEvent
from src.commands.cleanup_free_plan_data import cleanup_free_plan_analytics_data, get_free_plan_data_stats
from src.core.auth import get_password_hash
from src.core.config import settings


class TestFreeplanDataCleanup:
    """Test free plan data cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_data_for_free_users(self, async_session):
        """Test that cleanup removes old data for free plan users."""
        # Create a free user
        user = User(
            email="free@test.com",
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            subscription_tier="free",
            subscription_status="active"
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create API key for the user
        api_key = APIKey(
            package_name="test-package",
            key="klyne_test_key_123",
            user_id=user.id
        )
        async_session.add(api_key)
        await async_session.commit()

        # Create analytics events - some old, some new
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.FREE_PLAN_DATA_RETENTION_DAYS)
        
        # Create UUIDs for sessions
        old_session_1 = uuid4()
        old_session_2 = uuid4()
        new_session_1 = uuid4()
        new_session_2 = uuid4()
        
        # Old events (should be deleted)
        old_event1 = AnalyticsEvent(
            api_key=api_key.key,
            session_id=old_session_1,
            package_name="test-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=cutoff_date - timedelta(days=1),
        )
        old_event2 = AnalyticsEvent(
            api_key=api_key.key,
            session_id=old_session_2,
            package_name="test-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=cutoff_date - timedelta(hours=1),
        )
        
        # New events (should be kept)
        new_event1 = AnalyticsEvent(
            api_key=api_key.key,
            session_id=new_session_1,
            package_name="test-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=datetime.now(timezone.utc),
        )
        new_event2 = AnalyticsEvent(
            api_key=api_key.key,
            session_id=new_session_2,
            package_name="test-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=cutoff_date + timedelta(hours=1),
        )

        async_session.add_all([old_event1, old_event2, new_event1, new_event2])
        await async_session.commit()

        # Verify we have 4 events initially
        result = await async_session.execute(
            select(AnalyticsEvent).filter(AnalyticsEvent.api_key == api_key.key)
        )
        events_before = result.fetchall()
        assert len(events_before) == 4

        # Run cleanup
        cleanup_result = await cleanup_free_plan_analytics_data()
        
        # Verify cleanup results
        assert cleanup_result["success"] is True
        assert cleanup_result["total_deleted"] == 2
        assert cleanup_result["users_affected"] == 1
        assert cleanup_result["errors"] == []

        # Verify only new events remain
        result = await async_session.execute(
            select(AnalyticsEvent).filter(AnalyticsEvent.api_key == api_key.key)
        )
        events_after = result.fetchall()
        assert len(events_after) == 2
        
        # Verify the correct events remain
        remaining_session_ids = {event.AnalyticsEvent.session_id for event in events_after}
        assert remaining_session_ids == {new_session_1, new_session_2}

    @pytest.mark.asyncio
    async def test_cleanup_preserves_paid_user_data(self, async_session):
        """Test that cleanup preserves data for paid plan users."""
        # Create a starter user
        user = User(
            email="starter@test.com",
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            subscription_tier="starter",
            subscription_status="active"
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create API key for the user
        api_key = APIKey(
            package_name="paid-package",
            key="klyne_paid_key_123",
            user_id=user.id
        )
        async_session.add(api_key)
        await async_session.commit()

        # Create old analytics events
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.FREE_PLAN_DATA_RETENTION_DAYS + 5)
        
        old_event = AnalyticsEvent(
            api_key=api_key.key,
            session_id=uuid4(),
            package_name="paid-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=cutoff_date,
        )

        async_session.add(old_event)
        await async_session.commit()

        # Verify we have 1 event initially
        result = await async_session.execute(
            select(AnalyticsEvent).filter(AnalyticsEvent.api_key == api_key.key)
        )
        events_before = result.fetchall()
        assert len(events_before) == 1

        # Run cleanup
        cleanup_result = await cleanup_free_plan_analytics_data()
        
        # Verify cleanup results - no paid user data should be deleted
        assert cleanup_result["success"] is True
        assert cleanup_result["total_deleted"] == 0
        assert cleanup_result["users_affected"] == 0  # No free users found

        # Verify paid user's old event still exists
        result = await async_session.execute(
            select(AnalyticsEvent).filter(AnalyticsEvent.api_key == api_key.key)
        )
        events_after = result.fetchall()
        assert len(events_after) == 1

    @pytest.mark.asyncio
    async def test_cleanup_with_mixed_users(self, async_session):
        """Test cleanup with both free and paid users."""
        # Create free user
        free_user = User(
            email="free@test.com",
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            subscription_tier="free",
            subscription_status="active"
        )
        
        # Create paid user
        paid_user = User(
            email="paid@test.com",
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            subscription_tier="pro",
            subscription_status="active"
        )
        
        async_session.add_all([free_user, paid_user])
        await async_session.commit()
        await async_session.refresh(free_user)
        await async_session.refresh(paid_user)

        # Create API keys
        free_api_key = APIKey(
            package_name="free-package",
            key="klyne_free_key_123",
            user_id=free_user.id
        )
        paid_api_key = APIKey(
            package_name="paid-package",
            key="klyne_paid_key_123",
            user_id=paid_user.id
        )
        async_session.add_all([free_api_key, paid_api_key])
        await async_session.commit()

        # Create old events for both users
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.FREE_PLAN_DATA_RETENTION_DAYS + 1)
        
        free_old_event = AnalyticsEvent(
            api_key=free_api_key.key,
            session_id=uuid4(),
            package_name="free-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=cutoff_date,
        )
        
        paid_old_event = AnalyticsEvent(
            api_key=paid_api_key.key,
            session_id=uuid4(),
            package_name="paid-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=cutoff_date,
        )

        async_session.add_all([free_old_event, paid_old_event])
        await async_session.commit()

        # Run cleanup
        cleanup_result = await cleanup_free_plan_analytics_data()
        
        # Verify only free user's data was deleted
        assert cleanup_result["success"] is True
        assert cleanup_result["total_deleted"] == 1
        assert cleanup_result["users_affected"] == 1

        # Verify paid user's event still exists
        result = await async_session.execute(
            select(AnalyticsEvent).filter(AnalyticsEvent.api_key == paid_api_key.key)
        )
        paid_events = result.fetchall()
        assert len(paid_events) == 1

        # Verify free user's event was deleted
        result = await async_session.execute(
            select(AnalyticsEvent).filter(AnalyticsEvent.api_key == free_api_key.key)
        )
        free_events = result.fetchall()
        assert len(free_events) == 0

    @pytest.mark.asyncio
    async def test_cleanup_with_no_data(self, async_session):
        """Test cleanup when there's no data to clean up."""
        # Run cleanup with no data
        cleanup_result = await cleanup_free_plan_analytics_data()
        
        # Verify cleanup results
        assert cleanup_result["success"] is True
        assert cleanup_result["total_deleted"] == 0
        assert cleanup_result["users_affected"] == 0
        assert cleanup_result["errors"] == []

    @pytest.mark.asyncio
    async def test_get_free_plan_data_stats(self, async_session):
        """Test getting free plan data statistics."""
        # Create a free user with events
        user = User(
            email="free@test.com",
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            subscription_tier="free",
            subscription_status="active"
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create API key
        api_key = APIKey(
            package_name="test-package",
            key="klyne_test_key_123",
            user_id=user.id
        )
        async_session.add(api_key)
        await async_session.commit()

        # Create events - some old, some new
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.FREE_PLAN_DATA_RETENTION_DAYS)
        
        old_event = AnalyticsEvent(
            api_key=api_key.key,
            session_id=uuid4(),
            package_name="test-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=cutoff_date - timedelta(days=1),
        )
        
        new_event = AnalyticsEvent(
            api_key=api_key.key,
            session_id=uuid4(),
            package_name="test-package",
            package_version="1.0.0",
            python_version="3.9.0",
            os_type="Linux",
            event_timestamp=datetime.now(timezone.utc),
        )

        async_session.add_all([old_event, new_event])
        await async_session.commit()

        # Get stats
        stats = await get_free_plan_data_stats()
        
        # Verify stats
        assert stats["total_events"] == 2
        assert stats["old_events"] == 1
        assert stats["retention_days"] == settings.FREE_PLAN_DATA_RETENTION_DAYS
        assert "retention_cutoff" in stats

    @pytest.mark.asyncio
    async def test_cleanup_handles_no_free_users(self, async_session):
        """Test cleanup when there are no free users."""
        # Create only paid users
        user = User(
            email="paid@test.com",
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            subscription_tier="starter",
            subscription_status="active"
        )
        async_session.add(user)
        await async_session.commit()

        # Run cleanup
        cleanup_result = await cleanup_free_plan_analytics_data()
        
        # Verify results
        assert cleanup_result["success"] is True
        assert cleanup_result["total_deleted"] == 0
        assert cleanup_result["users_affected"] == 0
        assert cleanup_result["errors"] == []


class TestSubscriptionServiceLimits:
    """Test subscription service limits for different plans."""

    @pytest.mark.asyncio
    async def test_subscription_service_free_plan_limits(self, async_session):
        """Test subscription service returns correct limits for free plan."""
        from src.services.subscription_service import SubscriptionService
        from src.repositories.unit_of_work import SqlAlchemyUnitOfWork
        
        # Create free user
        user = User(
            email="free@test.com",
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            subscription_tier="free",
            subscription_status="active"
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create subscription service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = SubscriptionService(uow)

        # Get limits
        limits = await service.get_subscription_limits(user.id)
        
        # Verify free plan limits
        assert limits["subscription_tier"] == "free"
        assert limits["limits"]["max_api_keys"] == 1
        assert limits["limits"]["max_events_per_month"] == 3000
        assert limits["limits"]["max_packages"] == 1
        assert limits["limits"]["data_retention_days"] == 7
        assert "7_day_retention" in limits["limits"]["features"]

    @pytest.mark.asyncio
    async def test_subscription_service_starter_plan_limits(self, async_session):
        """Test subscription service returns correct limits for starter plan."""
        from src.services.subscription_service import SubscriptionService
        from src.repositories.unit_of_work import SqlAlchemyUnitOfWork
        
        # Create starter user
        user = User(
            email="starter@test.com",
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            subscription_tier="starter",
            subscription_status="active"
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create subscription service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = SubscriptionService(uow)

        # Get limits
        limits = await service.get_subscription_limits(user.id)
        
        # Verify starter plan limits
        assert limits["subscription_tier"] == "starter"
        assert limits["limits"]["max_api_keys"] == 1
        assert limits["limits"]["max_events_per_month"] == 10000
        assert limits["limits"]["max_packages"] == 1
        assert limits["limits"]["data_retention_days"] == -1  # Unlimited
        assert "unlimited_retention" in limits["limits"]["features"]
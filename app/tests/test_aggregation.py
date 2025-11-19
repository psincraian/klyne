"""Tests for dashboard aggregation functionality."""

import pytest_asyncio
from datetime import datetime, date, timedelta, timezone
from uuid import uuid4

from src.models.analytics_event import AnalyticsEvent
from src.models.api_key import APIKey
from src.models.user import User
from src.core.auth import get_password_hash
from src.services.analytics_service import AnalyticsService
from src.repositories.unit_of_work import SqlAlchemyUnitOfWork


class TestDashboardAggregation:
    """Test suite for dashboard data aggregation by day, week, and month."""

    @pytest_asyncio.fixture
    async def test_user_with_events(self, async_session):
        """Create a test user with API key and sample analytics events."""
        # Create test user
        user = User(
            email="aggregation_test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create test API key
        api_key = APIKey(
            package_name="test-package",
            key="klyne_test_aggregation_key",
            user_id=user.id,
        )
        async_session.add(api_key)
        await async_session.commit()
        await async_session.refresh(api_key)

        # Create test events over a 30-day period
        base_date = date.today() - timedelta(days=30)
        events = []

        for day in range(30):
            event_date = base_date + timedelta(days=day)
            event_datetime = datetime.combine(
                event_date, datetime.min.time()
            ).replace(tzinfo=timezone.utc)

            # Create 2-5 events per day to test aggregation
            for i in range((day % 4) + 2):  # 2-5 events per day
                event = AnalyticsEvent(
                    api_key=api_key.key,
                    session_id=uuid4(),
                    package_name="test-package",
                    package_version="1.0.0",
                    python_version="3.11.5",
                    os_type="Linux",
                    event_timestamp=event_datetime + timedelta(hours=i),
                    received_at=datetime.now(timezone.utc),
                    user_identifier=f"user_{day % 10}",  # 10 unique users cycling
                )
                events.append(event)
                async_session.add(event)

        await async_session.commit()

        return user, api_key, events

    async def test_daily_aggregation_default(
        self, async_session, test_user_with_events
    ):
        """Test that daily aggregation is the default."""
        user, api_key, _ = test_user_with_events

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Get data with default (daily) aggregation
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        result = await service.get_timeseries_data(
            user.id, None, start_date, end_date
        )

        # Should have dates array with daily data
        assert len(result.dates) > 0
        assert len(result.events) > 0
        # Daily aggregation should have more data points (30 days)
        assert len(result.dates) == 31  # inclusive range

    async def test_weekly_aggregation(
        self, async_session, test_user_with_events
    ):
        """Test weekly aggregation of dashboard data."""
        user, api_key, _ = test_user_with_events

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Get data with weekly aggregation
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        result = await service.get_timeseries_data(
            user.id, None, start_date, end_date, "week"
        )

        # Should have dates array with weekly data
        assert len(result.dates) > 0
        assert len(result.events) > 0
        assert len(result.sessions) > 0

        # Weekly aggregation should have fewer data points than daily
        # Approximately 4-6 weeks for 30 days
        assert 4 <= len(result.dates) <= 6

        # Events should be aggregated (summed) per week
        assert all(isinstance(count, int) for count in result.events)
        assert sum(result.events) > 0

    async def test_monthly_aggregation(
        self, async_session, test_user_with_events
    ):
        """Test monthly aggregation of dashboard data."""
        user, api_key, _ = test_user_with_events

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Get data with monthly aggregation (extending to 60 days for clearer test)
        end_date = date.today()
        start_date = end_date - timedelta(days=60)

        result = await service.get_timeseries_data(
            user.id, None, start_date, end_date, "month"
        )

        # Should have dates array with monthly data
        assert len(result.dates) > 0
        assert len(result.events) > 0

        # Monthly aggregation should have 2-3 data points for 60 days
        assert 2 <= len(result.dates) <= 3

        # Events should be aggregated per month
        assert all(isinstance(count, int) for count in result.events)

    async def test_aggregation_with_package_filter(
        self, async_session, test_user_with_events
    ):
        """Test aggregation works with package filtering."""
        user, api_key, _ = test_user_with_events

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Get data with weekly aggregation and package filter
        result = await service.get_timeseries_data(
            user.id, "test-package", None, None, "week"
        )

        assert len(result.dates) > 0
        assert "test-package" in result.packages

    async def test_invalid_aggregation_defaults_to_daily(
        self, async_session, test_user_with_events
    ):
        """Test that invalid aggregation period defaults to daily."""
        user, api_key, _ = test_user_with_events

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Get data with invalid aggregation (should default to daily)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        result = await service.get_timeseries_data(
            user.id, None, start_date, end_date, "invalid"
        )

        # Should default to daily aggregation (31 days inclusive)
        assert len(result.dates) == 31

    async def test_service_aggregate_by_week(self, async_session, test_user_with_events):
        """Test the _aggregate_by_week service method directly."""
        user, api_key, events = test_user_with_events

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Create sample dates_data
        today = date.today()
        dates_data = {}
        for i in range(14):  # 2 weeks of data
            date_str = (today - timedelta(days=i)).isoformat()
            dates_data[date_str] = {
                "events": 10 + i,
                "sessions": 5 + i,
                "unique_users": 3,
            }

        start_date = today - timedelta(days=13)
        end_date = today

        # Call the aggregation method
        date_range, events_list, sessions_list, unique_users_list = (
            service._aggregate_by_week(dates_data, start_date, end_date)
        )

        # Should have 2-3 weeks of data
        assert 2 <= len(date_range) <= 3
        assert len(date_range) == len(events_list)
        assert len(date_range) == len(sessions_list)
        assert len(date_range) == len(unique_users_list)

        # All dates should be Mondays (weekday() == 0)
        for date_str in date_range:
            dt = date.fromisoformat(date_str)
            assert dt.weekday() == 0  # Monday

    async def test_service_aggregate_by_month(
        self, async_session, test_user_with_events
    ):
        """Test the _aggregate_by_month service method directly."""
        user, api_key, events = test_user_with_events

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Create sample dates_data spanning 2 months
        today = date.today()
        dates_data = {}
        for i in range(60):  # 2 months of data
            date_str = (today - timedelta(days=i)).isoformat()
            dates_data[date_str] = {
                "events": 10 + i,
                "sessions": 5 + i,
                "unique_users": 3,
            }

        start_date = today - timedelta(days=59)
        end_date = today

        # Call the aggregation method
        date_range, events_list, sessions_list, unique_users_list = (
            service._aggregate_by_month(dates_data, start_date, end_date)
        )

        # Should have 2-3 months of data
        assert 2 <= len(date_range) <= 3
        assert len(date_range) == len(events_list)
        assert len(date_range) == len(sessions_list)
        assert len(date_range) == len(unique_users_list)

        # All dates should be first day of month
        for date_str in date_range:
            dt = date.fromisoformat(date_str)
            assert dt.day == 1  # First day of month

    async def test_aggregation_preserves_totals(
        self, async_session, test_user_with_events
    ):
        """Test that aggregation preserves total event counts."""
        user, api_key, events = test_user_with_events

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Get data with different aggregations
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        daily_data = await service.get_timeseries_data(
            user.id, None, start_date, end_date, "day"
        )
        weekly_data = await service.get_timeseries_data(
            user.id, None, start_date, end_date, "week"
        )
        monthly_data = await service.get_timeseries_data(
            user.id, None, start_date, end_date, "month"
        )

        # Total events should be the same across all aggregations
        daily_total = sum(daily_data.events)
        weekly_total = sum(weekly_data.events)
        monthly_total = sum(monthly_data.events)

        assert daily_total == weekly_total
        assert daily_total == monthly_total

    async def test_empty_data_aggregation(self, async_session):
        """Test aggregation with no data returns empty results."""
        # Create user without events
        user = User(
            email="empty_test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create service
        uow = SqlAlchemyUnitOfWork(async_session)
        service = AnalyticsService(uow)

        # Get data with weekly aggregation
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        result = await service.get_timeseries_data(
            user.id, None, start_date, end_date, "week"
        )

        # Should return empty data structure
        assert result.dates == []
        assert result.events == []
        assert result.sessions == []
        assert result.unique_users == []
        assert result.packages == []

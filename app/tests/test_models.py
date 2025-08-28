import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from src.models.user import User
from src.core.auth import get_password_hash


class TestUserModel:
    """Test User model functionality."""

    @pytest.mark.asyncio
    async def test_create_user(self, async_session):
        """Test creating a user."""
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=False,
            is_active=True,
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.is_verified is False
        assert user.is_active is True
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    @pytest.mark.asyncio
    async def test_user_unique_email(self, async_session):
        """Test that user emails are unique."""
        user1 = User(
            email="test@example.com",
            hashed_password=get_password_hash("password1"),
            is_verified=False,
            is_active=True,
        )
        async_session.add(user1)
        await async_session.commit()

        user2 = User(
            email="test@example.com",  # Same email
            hashed_password=get_password_hash("password2"),
            is_verified=False,
            is_active=True,
        )
        async_session.add(user2)

        with pytest.raises(Exception):  # Should raise integrity error
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_user_with_verification_token(self, async_session):
        """Test creating user with verification token."""
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            verification_token="test_token_123",
            verification_token_expires=datetime.now(timezone.utc),
            is_verified=False,
            is_active=True,
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        assert user.verification_token == "test_token_123"
        assert user.verification_token_expires is not None

    @pytest.mark.asyncio
    async def test_query_user_by_email(self, async_session):
        """Test querying user by email."""
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()

        # Query by email
        result = await async_session.execute(
            select(User).filter(User.email == "test@example.com")
        )
        found_user = result.scalar_one_or_none()

        assert found_user is not None
        assert found_user.email == "test@example.com"
        assert found_user.is_verified is True

    @pytest.mark.asyncio
    async def test_user_defaults(self, async_session):
        """Test user model defaults."""
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Test defaults
        assert user.is_verified is False
        assert user.is_active is True
        assert user.verification_token is None
        assert user.verification_token_expires is None

    @pytest.mark.asyncio
    async def test_free_plan_user_properties(self, async_session):
        """Test free plan user properties."""
        user = User(
            email="free@example.com",
            hashed_password=get_password_hash("testpassword123"),
            subscription_tier="free",
            subscription_status="active"
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Test free plan properties
        assert user.subscription_tier == "free"
        assert user.subscription_status == "active"
        assert user.is_free_plan is True
        assert user.has_active_subscription is True
        assert user.get_rate_limit_per_hour() == 100  # Free plan rate limit

    @pytest.mark.asyncio
    async def test_starter_plan_user_properties(self, async_session):
        """Test starter plan user properties."""
        user = User(
            email="starter@example.com",
            hashed_password=get_password_hash("testpassword123"),
            subscription_tier="starter",
            subscription_status="active"
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Test starter plan properties
        assert user.subscription_tier == "starter"
        assert user.subscription_status == "active"
        assert user.is_free_plan is False
        assert user.has_active_subscription is True
        assert user.get_rate_limit_per_hour() == 1000  # Paid plan rate limit

    @pytest.mark.asyncio
    async def test_pro_plan_user_properties(self, async_session):
        """Test pro plan user properties."""
        user = User(
            email="pro@example.com",
            hashed_password=get_password_hash("testpassword123"),
            subscription_tier="pro",
            subscription_status="active"
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Test pro plan properties
        assert user.subscription_tier == "pro"
        assert user.subscription_status == "active"
        assert user.is_free_plan is False
        assert user.has_active_subscription is True
        assert user.get_rate_limit_per_hour() == 1000  # Paid plan rate limit

    @pytest.mark.asyncio
    async def test_inactive_subscription_user_properties(self, async_session):
        """Test user with inactive subscription properties."""
        user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("testpassword123"),
            subscription_tier="starter",
            subscription_status="canceled"
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Test inactive subscription properties
        assert user.subscription_tier == "starter"
        assert user.subscription_status == "canceled"
        assert user.is_free_plan is False
        assert user.has_active_subscription is False
        assert user.get_rate_limit_per_hour() == 1000  # Still returns paid plan rate limit based on tier

    @pytest.mark.asyncio
    async def test_new_user_defaults_to_free_plan(self, async_session):
        """Test that new users default to free plan due to database defaults."""
        user = User(
            email="newuser@example.com",
            hashed_password=get_password_hash("testpassword123")
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Test that database defaults apply
        assert user.subscription_tier == "free"  # Database default
        assert user.subscription_status == "active"  # Database default
        assert user.is_free_plan is True
        assert user.has_active_subscription is True
        assert user.get_rate_limit_per_hour() == 100  # Free plan rate limit

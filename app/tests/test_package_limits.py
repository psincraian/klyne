"""
Tests for package limit functionality based on subscription tiers.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.models.api_key import APIKey
from src.core.subscription_utils import (
    get_package_limit_for_tier,
    can_user_create_package,
    get_user_package_usage,
)


class TestPackageLimits:
    """Test package limits for different subscription tiers."""

    async def test_get_package_limit_for_tier(self):
        """Test package limit calculation for different tiers."""
        # Free tier should have limit of 1
        assert await get_package_limit_for_tier("free", "active") == 1
        
        # Starter tier should have limit of 1
        assert await get_package_limit_for_tier("starter", "active") == 1
        
        # Pro tier should have unlimited packages (-1)
        assert await get_package_limit_for_tier("pro", "active") == -1
        
        # Enterprise tier should have unlimited packages (-1)
        assert await get_package_limit_for_tier("enterprise", "active") == -1
        
        # Inactive subscriptions should have no access
        assert await get_package_limit_for_tier("starter", "canceled") == 0
        assert await get_package_limit_for_tier("free", "canceled") == 0
        
        # Unknown tier should default to no access
        assert await get_package_limit_for_tier("unknown", "active") == 0

    async def test_free_user_can_create_first_package(self, db_session: AsyncSession):
        """Test that free users can create their first package."""
        # Create a free user with no API keys
        user = User(
            email="free@test.com",
            hashed_password="hashed",
            is_verified=True,
            subscription_tier="free",
            subscription_status="active"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Should be able to create first package
        can_create, error_msg, current, limit = await can_user_create_package(db_session, user.id)
        assert can_create is True
        assert error_msg == ""
        assert current == 0
        assert limit == 1

    async def test_free_user_cannot_create_second_package(self, db_session: AsyncSession):
        """Test that free users cannot create a second package."""
        # Create a free user
        user = User(
            email="free2@test.com",
            hashed_password="hashed",
            is_verified=True,
            subscription_tier="free",
            subscription_status="active"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create first API key
        api_key = APIKey(
            package_name="test-package",
            key="test-key",
            user_id=user.id
        )
        db_session.add(api_key)
        await db_session.commit()

        # Should NOT be able to create second package
        can_create, error_msg, current, limit = await can_user_create_package(db_session, user.id)
        assert can_create is False
        assert "limit of 1 package" in error_msg
        assert current == 1
        assert limit == 1

    async def test_starter_user_can_create_first_package(self, db_session: AsyncSession):
        """Test that starter users can create their first package."""
        # Create a starter user with no API keys
        user = User(
            email="starter@test.com",
            hashed_password="hashed",
            is_verified=True,
            subscription_tier="starter",
            subscription_status="active"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Should be able to create first package
        can_create, error_msg, current, limit = await can_user_create_package(db_session, user.id)
        assert can_create is True
        assert error_msg == ""
        assert current == 0
        assert limit == 1

    async def test_starter_user_cannot_create_second_package(self, db_session: AsyncSession):
        """Test that starter users cannot create a second package."""
        # Create a starter user
        user = User(
            email="starter2@test.com",
            hashed_password="hashed",
            is_verified=True,
            subscription_tier="starter",
            subscription_status="active"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create first API key
        api_key = APIKey(
            package_name="test-package",
            key="test-key",
            user_id=user.id
        )
        db_session.add(api_key)
        await db_session.commit()

        # Should NOT be able to create second package
        can_create, error_msg, current, limit = await can_user_create_package(db_session, user.id)
        assert can_create is False
        assert "limit of 1 package" in error_msg
        assert "upgrade to Pro" in error_msg
        assert current == 1
        assert limit == 1

    async def test_pro_user_can_create_multiple_packages(self, db_session: AsyncSession):
        """Test that pro users can create unlimited packages."""
        # Create a pro user
        user = User(
            email="pro@test.com",
            hashed_password="hashed",
            is_verified=True,
            subscription_tier="pro",
            subscription_status="active"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create multiple API keys
        for i in range(5):
            api_key = APIKey(
                package_name=f"test-package-{i}",
                key=f"test-key-{i}",
                user_id=user.id
            )
            db_session.add(api_key)
        await db_session.commit()

        # Should still be able to create more packages
        can_create, error_msg, current, limit = await can_user_create_package(db_session, user.id)
        assert can_create is True
        assert error_msg == ""
        assert current == 5
        assert limit == -1

    async def test_enterprise_user_can_create_multiple_packages(self, db_session: AsyncSession):
        """Test that enterprise users can create unlimited packages."""
        # Create an enterprise user
        user = User(
            email="enterprise@test.com",
            hashed_password="hashed",
            is_verified=True,
            subscription_tier="enterprise",
            subscription_status="active"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create multiple API keys
        for i in range(10):
            api_key = APIKey(
                package_name=f"enterprise-package-{i}",
                key=f"enterprise-key-{i}",
                user_id=user.id
            )
            db_session.add(api_key)
        await db_session.commit()

        # Should still be able to create more packages
        can_create, error_msg, current, limit = await can_user_create_package(db_session, user.id)
        assert can_create is True
        assert error_msg == ""
        assert current == 10
        assert limit == -1

    async def test_user_with_no_subscription_defaults_to_starter(self, db_session: AsyncSession):
        """Test that users with no subscription tier default to starter limits."""
        # Create a user with no subscription tier
        user = User(
            email="nosubscription@test.com",
            hashed_password="hashed",
            is_verified=True,
            subscription_tier=None,
            subscription_status=None
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Should have starter tier limits
        current, limit = await get_user_package_usage(db_session, user.id)
        assert current == 0
        assert limit == 1

    async def test_get_user_package_usage(self, db_session: AsyncSession):
        """Test getting user package usage statistics."""
        # Create a user
        user = User(
            email="usage@test.com",
            hashed_password="hashed",
            is_verified=True,
            subscription_tier="starter",
            subscription_status="active"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Initially should have 0 packages
        current, limit = await get_user_package_usage(db_session, user.id)
        assert current == 0
        assert limit == 1

        # Create an API key
        api_key = APIKey(
            package_name="usage-package",
            key="usage-key",
            user_id=user.id
        )
        db_session.add(api_key)
        await db_session.commit()

        # Should now have 1 package
        current, limit = await get_user_package_usage(db_session, user.id)
        assert current == 1
        assert limit == 1


class TestPackageLimitAPI:
    """Test package limit enforcement in API endpoints."""

    async def test_starter_user_blocked_from_creating_second_api_key(
        self, auth_client: AsyncClient, authenticated_starter_user_with_api_key
    ):
        """Test that starter users are blocked from creating a second API key."""
        # Try to create a second API key
        response = await auth_client.post(
            "/api/api-keys",
            data={"package_name": "second-package"}
        )
        
        # Should be forbidden
        assert response.status_code == 403
        assert "limit of 1 package" in response.json()["detail"]
        assert "upgrade to Pro" in response.json()["detail"]

    async def test_pro_user_can_create_multiple_api_keys(
        self, auth_client: AsyncClient, authenticated_pro_user
    ):
        """Test that pro users can create multiple API keys."""
        # Create first API key
        response = await auth_client.post(
            "/api/api-keys",
            data={"package_name": "first-package"}
        )
        assert response.status_code == 302  # Redirect to dashboard

        # Create second API key
        response = await auth_client.post(
            "/api/api-keys",
            data={"package_name": "second-package"}
        )
        assert response.status_code == 302  # Should succeed

        # Create third API key
        response = await auth_client.post(
            "/api/api-keys",
            data={"package_name": "third-package"}
        )
        assert response.status_code == 302  # Should succeed

    async def test_free_user_can_create_first_api_key(
        self, auth_client: AsyncClient, authenticated_free_user
    ):
        """Test that free users can create their first API key."""
        response = await auth_client.post(
            "/api/api-keys",
            data={"package_name": "first-package"}
        )
        assert response.status_code == 302  # Redirect to dashboard

    async def test_starter_user_can_create_first_api_key(
        self, auth_client: AsyncClient, authenticated_starter_user
    ):
        """Test that starter users can create their first API key."""
        response = await auth_client.post(
            "/api/api-keys",
            data={"package_name": "first-package"}
        )
        assert response.status_code == 302  # Redirect to dashboard
import pytest_asyncio
from sqlalchemy import select
from src.models.api_key import APIKey
from src.models.user import User
from src.core.auth import get_password_hash


class TestAPIKeyManagement:
    @pytest_asyncio.fixture
    async def test_user(self, async_session):
        """Create a test user."""
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        return user

    def test_api_key_generation(self):
        """Test API key generation format."""
        key = APIKey.generate_key()

        assert key.startswith("klyne_")
        assert len(key) > 40  # Should be long enough for security

        # Generate another key to ensure they're unique
        key2 = APIKey.generate_key()
        assert key != key2

    @pytest_asyncio.fixture
    async def test_api_key_model(self, test_user, async_session):
        """Test APIKey model creation and relationships."""
        # Create an API key
        api_key = APIKey(
            package_name="test-package", key=APIKey.generate_key(), user_id=test_user.id
        )
        async_session.add(api_key)
        await async_session.commit()
        await async_session.refresh(api_key)

        # Verify it was created correctly
        assert api_key.id is not None
        assert api_key.package_name == "test-package"
        assert api_key.key.startswith("klyne_")
        assert api_key.user_id == test_user.id
        assert api_key.created_at is not None

        # Test relationship
        api_key_from_db = await async_session.execute(
            select(APIKey).filter(APIKey.id == api_key.id)
        )
        api_key_from_db = api_key_from_db.scalar_one()

        assert api_key_from_db.package_name == "test-package"
        assert api_key_from_db.user_id == test_user.id

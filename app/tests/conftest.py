import os
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.models import Base
from src.core.database import get_db

# Set testing environment variable
os.environ["TESTING"] = "1"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    """Create an async engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Create an async session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def override_get_db(async_session):
    """Override the get_db dependency."""

    async def _override_get_db():
        try:
            yield async_session
            await async_session.commit()
        except Exception:
            await async_session.rollback()
            raise

    return _override_get_db


@pytest_asyncio.fixture
async def client(override_get_db):
    """Create test client with overridden database."""
    from httpx import ASGITransport

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(override_get_db):
    """Create test client with mock authentication."""
    from httpx import ASGITransport

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Store the original client as a context variable
        ac._auth_user_id = None
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "password_confirm": "testpassword123",
    }


@pytest.fixture
def invalid_user_data():
    """Invalid user data for testing."""
    return {
        "email": "invalid-email",
        "password": "short",
        "password_confirm": "different",
    }


@pytest_asyncio.fixture
async def db_session(async_session):
    """Alias for async_session to match test expectations."""
    return async_session


@pytest_asyncio.fixture 
async def authenticated_starter_user(auth_client: AsyncClient, async_session: AsyncSession):
    """Create an authenticated starter user."""
    from src.models.user import User
    from src.core.auth import get_password_hash
    
    # Create starter user
    user = User(
        email="starter@test.com",
        hashed_password=get_password_hash("password123"),
        is_verified=True,
        subscription_tier="starter"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Set authentication for the client
    auth_client._test_user_id = user.id
    
    return user


@pytest_asyncio.fixture 
async def authenticated_starter_user_with_api_key(auth_client: AsyncClient, async_session: AsyncSession):
    """Create an authenticated starter user with one API key."""
    from src.models.user import User
    from src.models.api_key import APIKey
    from src.core.auth import get_password_hash
    
    # Create starter user
    user = User(
        email="starter_with_key@test.com",
        hashed_password=get_password_hash("password123"),
        is_verified=True,
        subscription_tier="starter"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Create API key
    api_key = APIKey(
        package_name="existing-package",
        key="existing-key",
        user_id=user.id
    )
    async_session.add(api_key)
    await async_session.commit()
    
    # Set authentication for the client
    auth_client._test_user_id = user.id
    
    return user


@pytest_asyncio.fixture 
async def authenticated_pro_user(auth_client: AsyncClient, async_session: AsyncSession):
    """Create an authenticated pro user."""
    from src.models.user import User
    from src.core.auth import get_password_hash
    
    # Create pro user
    user = User(
        email="pro@test.com",
        hashed_password=get_password_hash("password123"),
        is_verified=True,
        subscription_tier="pro"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Set authentication for the client
    auth_client._test_user_id = user.id
    
    return user

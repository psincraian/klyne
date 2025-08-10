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

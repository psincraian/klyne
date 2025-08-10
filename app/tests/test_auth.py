import pytest
from httpx import AsyncClient
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from src.models.user import User
from src.core.auth import get_password_hash, generate_verification_token


class TestRegistration:
    """Test user registration functionality."""

    @pytest.mark.asyncio
    async def test_register_page_get(self, client: AsyncClient):
        """Test GET request to registration page."""
        response = await client.get("/register")
        assert response.status_code == 200
        assert "Create Account" in response.text

    @pytest.mark.asyncio
    async def test_register_user_success(
        self, client: AsyncClient, async_session, user_data
    ):
        """Test successful user registration."""
        response = await client.post("/register", data=user_data)
        assert response.status_code == 200
        assert "Account Created!" in response.text
        assert user_data["email"] in response.text

        # Verify user was created in database
        result = await async_session.execute(
            select(User).filter(User.email == user_data["email"])
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == user_data["email"]
        assert user.is_verified is False
        assert user.verification_token is not None

    @pytest.mark.asyncio
    async def test_register_user_password_mismatch(
        self, client: AsyncClient, user_data
    ):
        """Test registration with password mismatch."""
        user_data["password_confirm"] = "different_password"
        response = await client.post("/register", data=user_data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_user_short_password(self, client: AsyncClient, user_data):
        """Test registration with short password."""
        user_data["password"] = "short"
        user_data["password_confirm"] = "short"
        response = await client.post("/register", data=user_data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: AsyncClient, async_session, user_data
    ):
        """Test registration with duplicate email."""
        # First registration
        response = await client.post("/register", data=user_data)
        assert response.status_code == 200

        # Second registration with same email
        response = await client.post("/register", data=user_data)
        assert response.status_code == 400


class TestEmailVerification:
    """Test email verification functionality."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self, client: AsyncClient, async_session):
        """Test successful email verification."""
        # Create unverified user
        verification_token = generate_verification_token()
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            verification_token=verification_token,
            verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24),
            is_verified=False,
        )
        async_session.add(user)
        await async_session.commit()

        # Verify email
        response = await client.get(f"/verify?token={verification_token}")
        assert response.status_code == 200
        assert "Email Verified!" in response.text

        # Check user is verified
        await async_session.refresh(user)
        assert user.is_verified is True
        assert user.verification_token is None

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, client: AsyncClient):
        """Test email verification with invalid token."""
        response = await client.get("/verify?token=invalid_token")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(self, client: AsyncClient, async_session):
        """Test email verification with expired token."""
        # Create user with expired token
        verification_token = generate_verification_token()
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            verification_token=verification_token,
            verification_token_expires=datetime.now(timezone.utc)
            - timedelta(hours=1),  # Expired
            is_verified=False,
        )
        async_session.add(user)
        await async_session.commit()

        response = await client.get(f"/verify?token={verification_token}")
        assert response.status_code == 400


class TestLogin:
    """Test user login functionality."""

    @pytest.mark.asyncio
    async def test_login_page_get(self, client: AsyncClient):
        """Test GET request to login page."""
        response = await client.get("/login")
        assert response.status_code == 200
        assert "Welcome Back" in response.text

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, async_session):
        """Test successful login."""
        # Create verified user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()

        # Login
        login_data = {"email": "test@example.com", "password": "testpassword123"}
        response = await client.post("/login", data=login_data, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with invalid email."""
        login_data = {"email": "nonexistent@example.com", "password": "testpassword123"}
        response = await client.post("/login", data=login_data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, async_session):
        """Test login with invalid password."""
        # Create verified user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()

        # Login with wrong password
        login_data = {"email": "test@example.com", "password": "wrongpassword"}
        response = await client.post("/login", data=login_data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_unverified_user(self, client: AsyncClient, async_session):
        """Test login with unverified user."""
        # Create unverified user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=False,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()

        # Login
        login_data = {"email": "test@example.com", "password": "testpassword123"}
        response = await client.post("/login", data=login_data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, async_session):
        """Test login with inactive user."""
        # Create inactive user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=False,
        )
        async_session.add(user)
        await async_session.commit()

        # Login
        login_data = {"email": "test@example.com", "password": "testpassword123"}
        response = await client.post("/login", data=login_data)
        assert response.status_code == 400


class TestLogout:
    """Test user logout functionality."""

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient):
        """Test user logout."""
        response = await client.post("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/"


class TestDashboard:
    """Test dashboard functionality."""

    @pytest.mark.asyncio
    async def test_dashboard_authenticated(self, client: AsyncClient, async_session):
        """Test dashboard access for authenticated user."""
        # Create verified user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()

        # Login first
        login_data = {"email": "test@example.com", "password": "testpassword123"}
        await client.post("/login", data=login_data)

        # Access dashboard
        response = await client.get("/dashboard")
        assert response.status_code == 200
        assert "Welcome to Klyne" in response.text
        assert user.email in response.text

    @pytest.mark.asyncio
    async def test_dashboard_unauthenticated(self, client: AsyncClient):
        """Test dashboard access for unauthenticated user."""
        response = await client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/login"


class TestAuthenticationRedirects:
    """Test authentication-related redirects."""

    @pytest.mark.asyncio
    async def test_register_page_authenticated_user(
        self, client: AsyncClient, async_session
    ):
        """Test register page redirects authenticated user to dashboard."""
        # Create and login user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()

        login_data = {"email": "test@example.com", "password": "testpassword123"}
        await client.post("/login", data=login_data)

        # Try to access register page
        response = await client.get("/register", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

    @pytest.mark.asyncio
    async def test_login_page_authenticated_user(
        self, client: AsyncClient, async_session
    ):
        """Test login page redirects authenticated user to dashboard."""
        # Create and login user
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            is_verified=True,
            is_active=True,
        )
        async_session.add(user)
        await async_session.commit()

        login_data = {"email": "test@example.com", "password": "testpassword123"}
        await client.post("/login", data=login_data)

        # Try to access login page
        response = await client.get("/login", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

import pytest
from datetime import datetime, timezone, timedelta
from fastapi import Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse

from src.core.auth import (
    verify_password,
    get_password_hash,
    create_session,
    get_current_user_id,
    get_current_user_email,
    logout_user,
    is_authenticated,
    generate_verification_token,
    get_verification_token_expiry
)


class TestPasswordHashing:
    """Test password hashing utilities."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 20  # bcrypt hashes are long
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "testpassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Different hashes due to salt
        assert hash1 != hash2
        # But both verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestSessionManagement:
    """Test session management utilities."""
    
    @pytest.fixture
    def app_with_sessions(self):
        """Create a test app with session middleware."""
        app = Starlette()
        app.add_middleware(SessionMiddleware, secret_key="test-secret-key")
        
        @app.route("/test")
        async def test_endpoint(request):
            return JSONResponse({"status": "ok"})
        
        return app
    
    def test_session_creation_and_retrieval(self, app_with_sessions):
        """Test creating and retrieving session data."""
        client = TestClient(app_with_sessions)
        
        # Make a request to establish session
        response = client.get("/test")
        assert response.status_code == 200
        
        # Simulate session operations (would need actual request object in real scenario)
        # This is a simplified test of the functions
        
    def test_verification_token_generation(self):
        """Test verification token generation."""
        token1 = generate_verification_token()
        token2 = generate_verification_token()
        
        assert len(token1) > 10
        assert len(token2) > 10
        assert token1 != token2  # Should be unique
        assert isinstance(token1, str)
        assert isinstance(token2, str)
    
    def test_verification_token_expiry(self):
        """Test verification token expiry calculation."""
        expiry = get_verification_token_expiry()
        now = datetime.now(timezone.utc)
        
        assert expiry > now
        assert expiry <= now + timedelta(hours=25)  # Should be ~24 hours
        assert expiry >= now + timedelta(hours=23)


class TestSessionFunctions:
    """Test session-related functions with mock request."""
    
    class MockSession(dict):
        """Mock session for testing."""
        pass
    
    class MockRequest:
        """Mock request for testing."""
        def __init__(self):
            self.session = TestSessionFunctions.MockSession()
    
    def test_create_session(self):
        """Test session creation."""
        request = self.MockRequest()
        
        create_session(request, user_id=123, user_email="test@example.com")
        
        assert request.session["user_id"] == 123
        assert request.session["user_email"] == "test@example.com"
    
    def test_get_current_user_data(self):
        """Test getting current user data from session."""
        request = self.MockRequest()
        request.session["user_id"] = 123
        request.session["user_email"] = "test@example.com"
        
        assert get_current_user_id(request) == 123
        assert get_current_user_email(request) == "test@example.com"
    
    def test_get_current_user_data_empty_session(self):
        """Test getting user data from empty session."""
        request = self.MockRequest()
        
        assert get_current_user_id(request) is None
        assert get_current_user_email(request) is None
    
    def test_is_authenticated(self):
        """Test authentication check."""
        request = self.MockRequest()
        
        # Not authenticated initially
        assert is_authenticated(request) is False
        
        # Authenticated after setting user_id
        request.session["user_id"] = 123
        assert is_authenticated(request) is True
    
    def test_logout_user(self):
        """Test user logout."""
        request = self.MockRequest()
        request.session["user_id"] = 123
        request.session["user_email"] = "test@example.com"
        request.session["other_data"] = "should_be_cleared"
        
        logout_user(request)
        
        assert len(request.session) == 0
        assert "user_id" not in request.session
        assert "user_email" not in request.session
        assert "other_data" not in request.session
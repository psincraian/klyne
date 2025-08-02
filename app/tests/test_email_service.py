import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
import io
import sys

from src.services.email import EmailService


class TestEmailService:
    """Test email service functionality."""
    
    @pytest.mark.asyncio
    async def test_send_verification_email(self):
        """Test sending verification email."""
        email = "test@example.com"
        token = "test_verification_token"
        
        # Capture stdout to test console output
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        result = await EmailService.send_verification_email(email, token)
        
        # Restore stdout
        sys.stdout = sys.__stdout__
        
        assert result is True
        
        output = captured_output.getvalue()
        assert "EMAIL VERIFICATION" in output
        assert email in output
        assert token in output
        assert "http://localhost:8000/verify?token=" in output
    
    @pytest.mark.asyncio
    async def test_send_password_reset_email(self):
        """Test sending password reset email."""
        email = "test@example.com"
        token = "test_reset_token"
        
        # Capture stdout to test console output
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        result = await EmailService.send_password_reset_email(email, token)
        
        # Restore stdout
        sys.stdout = sys.__stdout__
        
        assert result is True
        
        output = captured_output.getvalue()
        assert "PASSWORD RESET" in output
        assert email in output
        assert token in output
        assert "http://localhost:8000/reset-password?token=" in output
    
    @pytest.mark.asyncio
    @patch('src.services.email.logger')
    async def test_send_verification_email_logging(self, mock_logger):
        """Test that verification email logs correctly."""
        email = "test@example.com"
        token = "test_verification_token"
        
        result = await EmailService.send_verification_email(email, token)
        
        assert result is True
        assert mock_logger.info.call_count >= 2
        
        # Check that email and URL are logged
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any(email in call for call in log_calls)
        assert any("Verification URL" in call for call in log_calls)
    
    @pytest.mark.asyncio
    @patch('src.services.email.logger')
    async def test_send_password_reset_email_logging(self, mock_logger):
        """Test that password reset email logs correctly."""
        email = "test@example.com"
        token = "test_reset_token"
        
        result = await EmailService.send_password_reset_email(email, token)
        
        assert result is True
        assert mock_logger.info.call_count >= 2
        
        # Check that email and URL are logged
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any(email in call for call in log_calls)
        assert any("Reset URL" in call for call in log_calls)
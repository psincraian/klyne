import io
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.email import EmailService


class TestEmailService:
    """Test email service functionality."""

    @pytest.fixture
    def mock_uow(self):
        """Create a mock Unit of Work."""
        uow = MagicMock()
        uow.emails = MagicMock()
        uow.emails.create_email_log = AsyncMock(return_value=MagicMock(id=1))
        uow.emails.update_email_status = AsyncMock()
        uow.emails.has_received_email_type = AsyncMock(return_value=False)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return uow

    @pytest.mark.asyncio
    async def test_send_verification_email(self, mock_uow):
        """Test sending verification email."""
        email = "test@example.com"
        token = "test_verification_token"
        user_id = 123

        # Capture stdout to test console output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        email_service = EmailService(mock_uow)
        result = await email_service.send_verification_email(email, token, user_id)

        # Restore stdout
        sys.stdout = sys.__stdout__

        assert result is True

        output = captured_output.getvalue()
        assert "EMAIL VERIFICATION" in output
        assert email in output
        assert token in output
        assert "http://localhost:8000/verify?token=" in output

        # Verify email log was created
        mock_uow.emails.create_email_log.assert_called_once()
        # Verify email status was updated
        mock_uow.emails.update_email_status.assert_called_once_with(1, "sent")
        # Verify transaction was committed
        mock_uow.commit.assert_called()

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self, mock_uow):
        """Test sending password reset email."""
        email = "test@example.com"
        token = "test_reset_token"
        user_id = 123

        # Capture stdout to test console output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        email_service = EmailService(mock_uow)
        result = await email_service.send_password_reset_email(email, token, user_id)

        # Restore stdout
        sys.stdout = sys.__stdout__

        assert result is True

        output = captured_output.getvalue()
        assert "PASSWORD RESET" in output
        assert email in output
        assert token in output
        assert "http://localhost:8000/reset-password?token=" in output

        # Verify email log was created
        mock_uow.emails.create_email_log.assert_called_once()
        # Verify email status was updated
        mock_uow.emails.update_email_status.assert_called_once_with(1, "sent")
        # Verify transaction was committed
        mock_uow.commit.assert_called()

    @pytest.mark.asyncio
    @patch("src.services.email.logger")
    async def test_send_verification_email_logging(self, mock_logger, mock_uow):
        """Test that verification email logs correctly."""
        email = "test@example.com"
        token = "test_verification_token"
        user_id = 123

        email_service = EmailService(mock_uow)
        result = await email_service.send_verification_email(email, token, user_id)

        assert result is True
        assert mock_logger.info.call_count >= 2

        # Check that email and URL are logged
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any(email in call for call in log_calls)
        assert any("Verification URL" in call for call in log_calls)

    @pytest.mark.asyncio
    @patch("src.services.email.logger")
    async def test_send_password_reset_email_logging(self, mock_logger, mock_uow):
        """Test that password reset email logs correctly."""
        email = "test@example.com"
        token = "test_reset_token"
        user_id = 123

        email_service = EmailService(mock_uow)
        result = await email_service.send_password_reset_email(email, token, user_id)

        assert result is True
        assert mock_logger.info.call_count >= 2

        # Check that email and URL are logged
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any(email in call for call in log_calls)
        assert any("Reset URL" in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_send_welcome_email(self, mock_uow):
        """Test sending welcome email."""
        email = "test@example.com"
        user_id = 123
        user_name = "test"

        # Capture stdout to test console output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        email_service = EmailService(mock_uow)
        result = await email_service.send_welcome_email(email, user_id, user_name)

        # Restore stdout
        sys.stdout = sys.__stdout__

        assert result is True

        output = captured_output.getvalue()
        assert "WELCOME EMAIL" in output
        assert email in output

        # Verify duplicate check was performed
        mock_uow.emails.has_received_email_type.assert_called_once_with(user_id, "welcome")
        # Verify email log was created
        mock_uow.emails.create_email_log.assert_called_once()
        # Verify email status was updated
        mock_uow.emails.update_email_status.assert_called_once_with(1, "sent")
        # Verify transaction was committed
        mock_uow.commit.assert_called()

    @pytest.mark.asyncio
    async def test_send_welcome_email_without_name(self, mock_uow):
        """Test sending welcome email without user name."""
        email = "test@example.com"
        user_id = 123

        # Capture stdout to test console output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        email_service = EmailService(mock_uow)
        result = await email_service.send_welcome_email(email, user_id)

        # Restore stdout
        sys.stdout = sys.__stdout__

        assert result is True

        output = captured_output.getvalue()
        assert "WELCOME EMAIL" in output
        assert email in output

    @pytest.mark.asyncio
    @patch("src.services.email.logger")
    async def test_send_welcome_email_logging(self, mock_logger, mock_uow):
        """Test that welcome email logs correctly."""
        email = "test@example.com"
        user_id = 123
        user_name = "test"

        email_service = EmailService(mock_uow)
        result = await email_service.send_welcome_email(email, user_id, user_name)

        assert result is True
        assert mock_logger.info.call_count >= 1

        # Check that email is logged
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any(email in call for call in log_calls)

    @pytest.mark.asyncio
    async def test_send_welcome_email_duplicate_prevention(self, mock_uow):
        """Test that welcome email is not sent if already sent."""
        email = "test@example.com"
        user_id = 123
        user_name = "test"

        # Mock that user already received welcome email
        mock_uow.emails.has_received_email_type = AsyncMock(return_value=True)

        email_service = EmailService(mock_uow)
        result = await email_service.send_welcome_email(email, user_id, user_name)

        assert result is True

        # Verify duplicate check was performed
        mock_uow.emails.has_received_email_type.assert_called_once_with(user_id, "welcome")
        # Verify email log was NOT created (since it's a duplicate)
        mock_uow.emails.create_email_log.assert_not_called()

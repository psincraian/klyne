import logging
import os
from datetime import datetime

import resend

from ..core.config import settings
from ..core.templates import templates

logger = logging.getLogger(__name__)

# Only set API key if it exists and we're not in test mode
if settings.RESEND_API_KEY and not os.getenv("TESTING"):
    resend.api_key = settings.RESEND_API_KEY


class EmailService:
    """Email service for sending verification emails."""

    @staticmethod
    async def send_verification_email(email: str, verification_token: str) -> bool:
        """Send verification email to user using Resend."""
        verification_url = f"{settings.APP_DOMAIN}/verify?token={verification_token}"

        # In test mode, just print to stdout and log
        if os.getenv("TESTING") or not settings.RESEND_API_KEY:
            print(f"EMAIL VERIFICATION - To: {email}")
            print(f"Verification URL: {verification_url}")
            logger.info(f"Test mode: Email verification would be sent to {email}")
            logger.info(f"Verification URL: {verification_url}")
            return True

        try:
            params: resend.Emails.SendParams = {
                "from": "Klyne <support@transactional.klyne.dev>",
                "to": [email],
                "subject": "Verify your Klyne account",
                "html": f"""
                <h2>Welcome to Klyne!</h2>
                <p>Please verify your email address by clicking the link below:</p>
                <p><a href="{verification_url}">Verify Email</a></p>
                <p>If you didn't create this account, you can safely ignore this email.</p>
                """,
            }

            email_result = resend.Emails.send(params)
            logger.info(
                f"Verification email sent to {email}, ID: {email_result.get('id')}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False

    @staticmethod
    async def send_password_reset_email(email: str, reset_token: str) -> bool:
        """Send password reset email to user using Resend."""
        reset_url = f"{settings.APP_DOMAIN}/reset-password?token={reset_token}"

        # In test mode, just print to stdout and log
        if os.getenv("TESTING") or not settings.RESEND_API_KEY:
            print(f"PASSWORD RESET - To: {email}")
            print(f"Reset URL: {reset_url}")
            logger.info(f"Test mode: Password reset email would be sent to {email}")
            logger.info(f"Reset URL: {reset_url}")
            return True

        try:
            params: resend.Emails.SendParams = {
                "from": "Klyne <support@transactional.klyne.dev>",
                "to": [email],
                "subject": "Reset your Klyne password",
                "html": f"""
                <h2>Password Reset Request</h2>
                <p>You requested a password reset for your Klyne account.</p>
                <p>Click the link below to reset your password:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>If you didn't request this reset, you can safely ignore this email.</p>
                """,
            }

            email_result = resend.Emails.send(params)
            logger.info(
                f"Password reset email sent to {email}, ID: {email_result.get('id')}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False

    @staticmethod
    async def send_welcome_email(email: str, user_name: str = None) -> bool:
        """Send welcome email to newly verified user using Resend and Jinja templates."""

        # In test mode, just print to stdout and log
        if os.getenv("TESTING") or not settings.RESEND_API_KEY:
            print(f"WELCOME EMAIL - To: {email}")
            logger.info(f"Test mode: Welcome email would be sent to {email}")
            return True

        try:
            # Create greeting
            greeting = f"Hey {user_name}," if user_name else "Hey,"

            # Template context
            context = {
                "greeting": greeting,
                "app_domain": settings.APP_DOMAIN,
                "current_year": datetime.now().year,
            }

            # Render templates
            html_content = templates.get_template("emails/welcome.html").render(context)

            params: resend.Emails.SendParams = {
                "from": "Petru from Klyne <petru@klyne.dev>",
                "to": [email],
                "subject": "Welcome to Klyne!",
                "html": html_content,
            }

            email_result = resend.Emails.send(params)
            logger.info(f"Welcome email sent to {email}, ID: {email_result.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False

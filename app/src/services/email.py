from typing import Optional
import logging
import resend
from ..core.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


class EmailService:
    """Email service for sending verification emails."""
    
    @staticmethod
    async def send_verification_email(email: str, verification_token: str) -> bool:
        """Send verification email to user using Resend."""
        verification_url = f"http://localhost:8000/verify?token={verification_token}"
        
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
            logger.info(f"Verification email sent to {email}, ID: {email_result.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False
    
    @staticmethod
    async def send_password_reset_email(email: str, reset_token: str) -> bool:
        """Send password reset email to user using Resend."""
        reset_url = f"http://localhost:8000/reset-password?token={reset_token}"
        
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
            logger.info(f"Password reset email sent to {email}, ID: {email_result.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False
import logging
import os
from datetime import datetime
from typing import Optional

import resend

from ..core.config import settings
from ..repositories.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)

# Only set API key if it exists and we're not in test mode
if settings.RESEND_API_KEY and not os.getenv("TESTING"):
    resend.api_key = settings.RESEND_API_KEY


class EmailService:
    """Email service for sending emails with database logging."""

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def send_verification_email(self, email: str, verification_token: str, user_id: Optional[int] = None) -> bool:
        """Send verification email to user using Resend."""
        verification_url = f"{settings.APP_DOMAIN}/verify?token={verification_token}"
        subject = "Verify your Klyne account"
        
        # Log email attempt first
        email_log = await self.uow.emails.create_email_log(
            email_address=email,
            email_type="verification",
            subject=subject,
            user_id=user_id,
            status="pending"
        )

        # In test mode, just print to stdout and log
        if os.getenv("TESTING") or not settings.RESEND_API_KEY:
            print(f"EMAIL VERIFICATION - To: {email}")
            print(f"Verification URL: {verification_url}")
            logger.info(f"Test mode: Email verification would be sent to {email}")
            logger.info(f"Verification URL: {verification_url}")
            
            # Update log as sent in test mode
            await self.uow.emails.update_email_status(email_log.id, "sent")
            await self.uow.commit()
            return True

        try:
            params: resend.Emails.SendParams = {
                "from": "Klyne <support@transactional.klyne.dev>",
                "to": [email],
                "subject": subject,
                "html": f"""
                <h2>Welcome to Klyne!</h2>
                <p>Please verify your email address by clicking the link below:</p>
                <p><a href="{verification_url}">Verify Email</a></p>
                <p>If you didn't create this account, you can safely ignore this email.</p>
                """,
            }

            email_result = resend.Emails.send(params)
            
            # Update email log with success
            await self.uow.emails.update_email_status(
                email_log.id, 
                "sent",
                None  # No error message on success
            )
            
            # Store resend ID in metadata
            email_log.email_metadata = {"resend_id": email_result.get("id")}
            await self.uow.commit()
            
            logger.info(f"Verification email sent to {email}, ID: {email_result.get('id')}")
            return True

        except Exception as e:
            # Update email log with failure
            await self.uow.emails.update_email_status(
                email_log.id,
                "failed", 
                str(e)
            )
            await self.uow.commit()
            
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False

    async def send_password_reset_email(self, email: str, reset_token: str, user_id: Optional[int] = None) -> bool:
        """Send password reset email to user using Resend."""
        reset_url = f"{settings.APP_DOMAIN}/reset-password?token={reset_token}"
        subject = "Reset your Klyne password"
        
        # Log email attempt first
        email_log = await self.uow.emails.create_email_log(
            email_address=email,
            email_type="password_reset",
            subject=subject,
            user_id=user_id,
            status="pending"
        )

        # In test mode, just print to stdout and log
        if os.getenv("TESTING") or not settings.RESEND_API_KEY:
            print(f"PASSWORD RESET - To: {email}")
            print(f"Reset URL: {reset_url}")
            logger.info(f"Test mode: Password reset email would be sent to {email}")
            logger.info(f"Reset URL: {reset_url}")
            
            # Update log as sent in test mode
            await self.uow.emails.update_email_status(email_log.id, "sent")
            await self.uow.commit()
            return True

        try:
            params: resend.Emails.SendParams = {
                "from": "Klyne <support@transactional.klyne.dev>",
                "to": [email],
                "subject": subject,
                "html": f"""
                <h2>Password Reset Request</h2>
                <p>You requested a password reset for your Klyne account.</p>
                <p>Click the link below to reset your password:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>If you didn't request this reset, you can safely ignore this email.</p>
                """,
            }

            email_result = resend.Emails.send(params)
            
            # Update email log with success
            await self.uow.emails.update_email_status(
                email_log.id,
                "sent",
                None
            )
            
            # Store resend ID in metadata
            email_log.email_metadata = {"resend_id": email_result.get("id")}
            await self.uow.commit()
            
            logger.info(f"Password reset email sent to {email}, ID: {email_result.get('id')}")
            return True

        except Exception as e:
            # Update email log with failure
            await self.uow.emails.update_email_status(
                email_log.id,
                "failed",
                str(e)
            )
            await self.uow.commit()
            
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False

    async def send_welcome_email(self, email: str, user_id: int, user_name: str | None = None) -> bool:
        """Send welcome email to newly verified user using Resend and Jinja templates."""
        subject = "Welcome to Klyne!"
        
        # Check if welcome email already sent to prevent duplicates
        if await self.uow.emails.has_received_email_type(user_id, "welcome"):
            logger.info(f"Welcome email already sent to user {user_id} ({email}), skipping")
            return True
        
        # Log email attempt first
        email_log = await self.uow.emails.create_email_log(
            email_address=email,
            email_type="welcome",
            subject=subject,
            user_id=user_id,
            status="pending"
        )

        # In test mode, just print to stdout and log
        if os.getenv("TESTING") or not settings.RESEND_API_KEY:
            print(f"WELCOME EMAIL - To: {email}")
            logger.info(f"Test mode: Welcome email would be sent to {email}")
            
            # Update log as sent in test mode
            await self.uow.emails.update_email_status(email_log.id, "sent")
            await self.uow.commit()
            return True

        try:
            # Create greeting
            greeting = f"Hey {user_name}," if user_name else "Hey,"

            # Create personal plain text email content
            text_content = f"""{greeting}

Welcome to Klyne! 🎉

I'm Petru, and I built Klyne because I was curious about who was actually using my Python packages. Are they running on Linux servers? Windows desktops? Python 3.12 or still stuck on 3.8? I had no idea!

Now you can find out too.

Here's how to get your first insights:

📊 Step 1: Grab your API key
Head to your dashboard at {settings.APP_DOMAIN}/dashboard and create your first API key. Takes about 30 seconds.

🔌 Step 2: Drop one line into your package
Add klyne.init(api_key='your-key', project='your-package') somewhere in your package initialization.
That's it!

📈 Step 3: Watch the data roll in
Your analytics dashboard will start showing you real usage patterns - which Python versions, operating systems, and how your package is actually being used in the wild.

💡 Privacy note: The integration is designed to be lightweight and privacy-friendly. We only collect anonymous technical metadata, never user data or code.

Want to see it in action? Check out our docs at {settings.APP_DOMAIN}/docs for examples and integration guides.

Got questions? Hit reply - I read every email and love hearing from developers using Klyne.

Happy coding!
Petru

P.S. If you run into any issues or have ideas for features, I'm always here to help. Just reply to this email.

---
You're getting this email because you signed up for Klyne.
© {datetime.now().year} Klyne. All rights reserved."""

            params: resend.Emails.SendParams = {
                "from": "Petru from Klyne <support@transactional.klyne.dev>",
                "to": [email],
                "reply_to": ["petru@klyne.dev"],
                "subject": subject,
                "text": text_content,
            }

            email_result = resend.Emails.send(params)
            
            # Update email log with success
            await self.uow.emails.update_email_status(
                email_log.id,
                "sent",
                None
            )
            
            # Store resend ID in metadata
            email_log.email_metadata = {
                "resend_id": email_result.get("id"),
                "user_name": user_name
            }
            await self.uow.commit()
            
            logger.info(f"Welcome email sent to {email}, ID: {email_result.get('id')}")
            return True

        except Exception as e:
            # Update email log with failure
            await self.uow.emails.update_email_status(
                email_log.id,
                "failed",
                str(e)
            )
            await self.uow.commit()
            
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False

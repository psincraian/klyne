#!/usr/bin/env python3
"""
Script to send apology emails with verification codes to users registered in the last week.

This script is designed to handle the registration error by re-sending verification
emails to all users who registered in the last 7 days.

Usage:
    uv run python -m src.scripts.send_apology_emails
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import generate_verification_token, get_verification_token_expiry
from src.core.config import settings
from src.core.database import engine, get_db
from src.models.user import User
from src.repositories.unit_of_work import SqlAlchemyUnitOfWork
from src.services.email import EmailService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def send_apology_email(email: str, verification_token: str, user_id: int) -> bool:
    """Send apology email with verification link."""
    verification_url = f"{settings.APP_DOMAIN}/verify?token={verification_token}"
    subject = "We apologize - Please verify your Klyne account"

    import resend

    try:
        params: resend.Emails.SendParams = {
            "from": "Petru from Klyne <support@transactional.klyne.dev>",
            "to": [email],
            "reply_to": ["petru@klyne.dev"],
            "subject": subject,
            "html": f"""
            <h2>We apologize for the inconvenience</h2>
            <p>Dear Klyne user,</p>

            <p>We recently experienced a technical issue with our user registration system.
            We sincerely apologize for any confusion this may have caused.</p>

            <p>To ensure your account is properly set up, please verify your email address
            by clicking the button below:</p>

            <p style="margin: 30px 0;">
                <a href="{verification_url}" style="background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                    Verify My Email
                </a>
            </p>

            <p>Or copy and paste this link into your browser:</p>
            <p><a href="{verification_url}">{verification_url}</a></p>

            <p>This verification link will expire in 24 hours for security reasons.</p>

            <p>If you have any questions or concerns, please don't hesitate to reply to this email.
            I personally read every message.</p>

            <p>Thank you for your patience and understanding.</p>

            <p>Best regards,<br>
            Petru<br>
            Founder, Klyne</p>

            <hr style="margin-top: 30px; border: none; border-top: 1px solid #e5e7eb;">
            <p style="color: #6b7280; font-size: 12px;">
                You're receiving this email because you recently registered for Klyne.<br>
                © {datetime.now().year} Klyne. All rights reserved.
            </p>
            """,
            "text": f"""We apologize for the inconvenience

Dear Klyne user,

We recently experienced a technical issue with our user registration system.
We sincerely apologize for any confusion this may have caused.

To ensure your account is properly set up, please verify your email address
by clicking the link below:

{verification_url}

This verification link will expire in 24 hours for security reasons.

If you have any questions or concerns, please don't hesitate to reply to this email.
I personally read every message.

Thank you for your patience and understanding.

Best regards,
Petru
Founder, Klyne

---
You're receiving this email because you recently registered for Klyne.
© {datetime.now().year} Klyne. All rights reserved.
""",
        }

        email_result = resend.Emails.send(params)
        logger.info(f"Apology email sent to {email}, Resend ID: {email_result.get('id')}")
        return True

    except Exception as e:
        logger.error(f"Failed to send apology email to {email}: {str(e)}")
        return False


async def send_apology_emails_to_recent_users():
    """
    Fetch all users registered in the last week and send them apology emails
    with fresh verification tokens.
    """
    logger.info("Starting apology email send process...")

    # Create async session
    from src.core.database import async_session_maker

    async with async_session_maker() as db:
        try:
            # Calculate the date 7 days ago
            one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

            # Query for users created in the last week
            result = await db.execute(
                select(User).where(User.created_at >= one_week_ago).order_by(User.created_at.desc())
            )
            users = result.scalars().all()

            logger.info(f"Found {len(users)} users registered in the last 7 days")

            if not users:
                logger.info("No users found in the last week. Exiting.")
                return

            success_count = 0
            failure_count = 0

            for user in users:
                try:
                    logger.info(
                        f"Processing user: {user.email} (ID: {user.id}, Registered: {user.created_at})"
                    )

                    # Generate a new verification token (even if they already have one)
                    verification_token = generate_verification_token()
                    token_expiry = get_verification_token_expiry()

                    # Update the user's verification token
                    user.verification_token = verification_token
                    user.verification_token_expires = token_expiry

                    await db.commit()
                    logger.info(f"Generated new verification token for {user.email}")

                    # Send the apology email with the verification link
                    email_sent = await send_apology_email(
                        user.email, verification_token, user.id
                    )

                    if email_sent:
                        success_count += 1
                        logger.info(f"✓ Successfully sent apology email to {user.email}")
                    else:
                        failure_count += 1
                        logger.error(f"✗ Failed to send apology email to {user.email}")

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    failure_count += 1
                    logger.error(
                        f"Error processing user {user.email}: {str(e)}", exc_info=True
                    )
                    await db.rollback()

            logger.info("=" * 60)
            logger.info("APOLOGY EMAIL SEND SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total users found: {len(users)}")
            logger.info(f"Successfully sent: {success_count}")
            logger.info(f"Failed: {failure_count}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Fatal error in apology email process: {str(e)}", exc_info=True)
            await db.rollback()
            raise


async def main():
    """Main entry point for the script."""
    logger.info("=" * 60)
    logger.info("APOLOGY EMAIL SCRIPT")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"App Domain: {settings.APP_DOMAIN}")
    logger.info(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    # Confirm before proceeding
    print("\n⚠️  WARNING: This script will send emails to all users registered in the last 7 days.")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"App Domain: {settings.APP_DOMAIN}")
    response = input("\nDo you want to proceed? (yes/no): ")

    if response.lower() not in ["yes", "y"]:
        logger.info("Script cancelled by user.")
        print("Script cancelled.")
        return

    try:
        await send_apology_emails_to_recent_users()
        logger.info("Script completed successfully")
        print("\n✓ Script completed successfully!")
    except Exception as e:
        logger.error(f"Script failed: {str(e)}", exc_info=True)
        print(f"\n✗ Script failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

"""
Welcome email scheduler task.
Sends welcome emails to users 24+ hours after registration.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from sqlalchemy import and_, select

from src.core.database import get_db_session
from src.models.email import Email
from src.models.user import User
from src.repositories.unit_of_work import SqlAlchemyUnitOfWork
from src.services.email import EmailService


class TaskResult(TypedDict):
    """Result structure for task execution."""
    processed_users: int
    emails_sent: int
    emails_failed: int
    errors: list[str]

logger = logging.getLogger(__name__)


async def send_welcome_emails() -> TaskResult:
    """
    Send welcome emails to users who registered 24+ hours ago
    and haven't received a welcome email yet.

    Returns:
        Dict containing execution results
    """
    results: TaskResult = {"processed_users": 0, "emails_sent": 0, "emails_failed": 0, "errors": []}

    try:
        async with get_db_session() as session:
            uow = SqlAlchemyUnitOfWork(session)
            email_service = EmailService(uow)

            # Find users who registered 24+ hours ago
            twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=48)

            # Query users who:
            # 1. Were created 48+ hours ago
            # 2. Are verified (email confirmed)
            # 3. Are active
            # 4. Haven't received a welcome email yet
            query = select(User).where(
                and_(
                    User.created_at <= twenty_four_hours_ago,
                    User.is_verified,
                    User.is_active,
                    # Check that no welcome email has been sent to this user
                    ~select(Email)
                    .where(
                        and_(
                            Email.user_id == User.id,
                            Email.email_type == "welcome",
                            Email.status == "sent",
                        )
                    )
                    .exists(),
                )
            )

            result = await session.execute(query)
            eligible_users = result.scalars().all()

            logger.info(
                f"Found {len(eligible_users)} users eligible for welcome emails"
            )

            for user in eligible_users:
                results["processed_users"] += 1

                try:
                    # Extract name from email for personalization
                    user_name = user.email.split("@")[0] if user.email else None

                    # Send welcome email
                    success = await email_service.send_welcome_email(
                        email=user.email, user_id=user.id, user_name=user_name
                    )

                    if success:
                        results["emails_sent"] += 1
                        logger.info(f"Welcome email sent successfully to {user.email}")
                    else:
                        results["emails_failed"] += 1
                        logger.error(f"Failed to send welcome email to {user.email}")

                except Exception as e:
                    results["emails_failed"] += 1
                    error_msg = f"Error sending welcome email to {user.email}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)

            logger.info(
                f"Welcome email task completed. "
                f"Processed: {results['processed_users']}, "
                f"Sent: {results['emails_sent']}, "
                f"Failed: {results['emails_failed']}"
            )

    except Exception as e:
        error_msg = f"Critical error in welcome email task: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(error_msg)
        raise

    return results


# For testing purposes
async def send_welcome_emails_to_specific_user(user_id: int) -> bool:
    """
    Send a welcome email to a specific user (for testing).

    Args:
        user_id: The ID of the user to send the welcome email to

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        async with get_db_session() as session:
            uow = SqlAlchemyUnitOfWork(session)
            email_service = EmailService(uow)

            # Get user by ID
            user = await uow.users.get_by_id(user_id)
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return False

            if not user.is_verified:
                logger.error(f"User {user_id} is not verified yet")
                return False

            # Extract name from email for personalization
            user_name = user.email.split("@")[0] if user.email else None

            # Send welcome email
            success = await email_service.send_welcome_email(
                email=user.email, user_id=user.id, user_name=user_name
            )

            if success:
                logger.info(
                    f"Welcome email sent successfully to user {user_id} ({user.email})"
                )
            else:
                logger.error(
                    f"Failed to send welcome email to user {user_id} ({user.email})"
                )

            return success

    except Exception as e:
        logger.error(f"Error sending welcome email to user {user_id}: {str(e)}")
        return False

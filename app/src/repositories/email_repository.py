from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.email import Email


class EmailRepository:
    """Repository for email operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_email_log(
        self,
        email_address: str,
        email_type: str,
        subject: str,
        user_id: Optional[int] = None,
        status: str = "sent",
        error_message: Optional[str] = None,
        email_metadata: Optional[dict] = None,
    ) -> Email:
        """Create a new email log entry."""
        email_log = Email(
            user_id=user_id,
            email_address=email_address,
            email_type=email_type,
            subject=subject,
            status=status,
            error_message=error_message,
            email_metadata=email_metadata,
        )
        
        self.db.add(email_log)
        await self.db.flush()
        await self.db.refresh(email_log)
        
        return email_log

    async def has_received_email_type(self, user_id: int, email_type: str) -> bool:
        """Check if a user has received a specific type of email."""
        result = await self.db.execute(
            select(Email).filter(
                Email.user_id == user_id,
                Email.email_type == email_type,
                Email.status == "sent"
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def has_received_email_type_by_email(self, email_address: str, email_type: str) -> bool:
        """Check if an email address has received a specific type of email."""
        result = await self.db.execute(
            select(Email).filter(
                Email.email_address == email_address,
                Email.email_type == email_type,
                Email.status == "sent"
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_emails_by_user(self, user_id: int, limit: int = 50) -> List[Email]:
        """Get all emails sent to a specific user."""
        result = await self.db.execute(
            select(Email)
            .filter(Email.user_id == user_id)
            .order_by(Email.sent_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_emails_by_type(
        self, 
        email_type: str, 
        status: Optional[str] = None, 
        limit: int = 100
    ) -> List[Email]:
        """Get emails by type and optionally by status."""
        query = select(Email).filter(Email.email_type == email_type)
        
        if status:
            query = query.filter(Email.status == status)
            
        query = query.order_by(Email.sent_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_email_status(
        self, 
        email_id: int, 
        status: str, 
        error_message: Optional[str] = None
    ) -> Optional[Email]:
        """Update the status of an email log entry."""
        result = await self.db.execute(
            select(Email).filter(Email.id == email_id)
        )
        email_log = result.scalar_one_or_none()
        
        if email_log:
            email_log.status = status
            email_log.error_message = error_message
            email_log.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(email_log)
            
        return email_log

    async def get_failed_emails(self, limit: int = 100) -> List[Email]:
        """Get all failed emails for retry attempts."""
        result = await self.db.execute(
            select(Email)
            .filter(Email.status == "failed")
            .order_by(Email.sent_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
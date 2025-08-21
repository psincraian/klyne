from typing import Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.email_signup import EmailSignup
from src.repositories.base import BaseRepository


class EmailSignupRepository(BaseRepository[EmailSignup]):
    """Repository for EmailSignup model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, EmailSignup)

    async def get_by_email(self, email: str) -> Optional[EmailSignup]:
        """Get email signup by email address."""
        result = await self.db.execute(
            select(EmailSignup).filter(EmailSignup.email == email)
        )
        return result.scalar_one_or_none()

    async def create_signup(self, email: str) -> EmailSignup:
        """Create a new email signup."""
        return await self.create({"email": email})

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists in signups."""
        result = await self.db.execute(
            select(EmailSignup.id).filter(EmailSignup.email == email)
        )
        return result.scalar_one_or_none() is not None

    async def get_recent_signups(self, days: int = 7) -> List[EmailSignup]:
        """Get recent signups within specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(EmailSignup)
            .filter(EmailSignup.created_at >= cutoff_date)
            .order_by(desc(EmailSignup.created_at))
        )
        return list(result.scalars().all())

    async def get_signups_by_date_range(self, start_date: date, end_date: date) -> List[EmailSignup]:
        """Get signups within a date range."""
        result = await self.db.execute(
            select(EmailSignup)
            .filter(
                func.date(EmailSignup.created_at) >= start_date,
                func.date(EmailSignup.created_at) <= end_date
            )
            .order_by(desc(EmailSignup.created_at))
        )
        return list(result.scalars().all())

    async def count_signups_by_date(self, target_date: date) -> int:
        """Count signups for a specific date."""
        result = await self.db.execute(
            select(func.count(EmailSignup.id))
            .filter(func.date(EmailSignup.created_at) == target_date)
        )
        return result.scalar()

    async def get_daily_signup_counts(self, days: int = 30) -> List[tuple]:
        """Get daily signup counts for the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(
                func.date(EmailSignup.created_at).label("signup_date"),
                func.count(EmailSignup.id).label("count")
            )
            .filter(EmailSignup.created_at >= cutoff_date)
            .group_by(func.date(EmailSignup.created_at))
            .order_by(func.date(EmailSignup.created_at))
        )
        return result.all()

    async def get_total_signups_count(self) -> int:
        """Get total number of email signups."""
        return await self.count()

    async def get_latest_signups(self, limit: int = 10) -> List[EmailSignup]:
        """Get the latest email signups."""
        result = await self.db.execute(
            select(EmailSignup)
            .order_by(desc(EmailSignup.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_email_pattern(self, pattern: str) -> List[EmailSignup]:
        """Search signups by email pattern (useful for finding domains, etc.)."""
        result = await self.db.execute(
            select(EmailSignup)
            .filter(EmailSignup.email.like(f"%{pattern}%"))
            .order_by(desc(EmailSignup.created_at))
        )
        return list(result.scalars().all())

    async def get_signup_stats(self) -> dict:
        """Get comprehensive signup statistics."""
        # Total signups
        total = await self.count()
        
        # Today's signups
        today = date.today()
        today_count = await self.count_signups_by_date(today)
        
        # This week's signups
        week_ago = today - timedelta(days=7)
        this_week_result = await self.db.execute(
            select(func.count(EmailSignup.id))
            .filter(func.date(EmailSignup.created_at) >= week_ago)
        )
        this_week_count = this_week_result.scalar()
        
        # This month's signups
        month_ago = today - timedelta(days=30)
        this_month_result = await self.db.execute(
            select(func.count(EmailSignup.id))
            .filter(func.date(EmailSignup.created_at) >= month_ago)
        )
        this_month_count = this_month_result.scalar()
        
        return {
            "total": total,
            "today": today_count,
            "this_week": this_week_count,
            "this_month": this_month_count
        }
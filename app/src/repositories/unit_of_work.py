from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.repositories.user_repository import UserRepository
from src.repositories.api_key_repository import APIKeyRepository
from src.repositories.analytics_event_repository import AnalyticsEventRepository
from src.repositories.email_signup_repository import EmailSignupRepository
from src.repositories.email_repository import EmailRepository

logger = logging.getLogger(__name__)


class AbstractUnitOfWork(ABC):
    """Abstract Unit of Work pattern for managing database transactions."""
    
    users: UserRepository
    api_keys: APIKeyRepository
    analytics_events: AnalyticsEventRepository
    email_signups: EmailSignupRepository
    emails: EmailRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """SQLAlchemy implementation of Unit of Work pattern."""

    def __init__(self, session: AsyncSession):
        self.session = session
        # Initialize repositories with the session
        self.users = UserRepository(self.session)
        self.api_keys = APIKeyRepository(self.session)
        self.analytics_events = AnalyticsEventRepository(self.session)
        self.email_signups = EmailSignupRepository(self.session)
        self.emails = EmailRepository(self.session)
        
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self):
        """Commit the current transaction."""
        try:
            await self.session.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            await self.rollback()
            raise

    async def rollback(self):
        """Rollback the current transaction."""
        try:
            await self.session.rollback()
            logger.debug("Transaction rolled back")
        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            raise

    async def flush(self):
        """Flush pending changes to the database without committing."""
        try:
            await self.session.flush()
            logger.debug("Session flushed successfully")
        except Exception as e:
            logger.error(f"Error flushing session: {e}")
            raise

    async def refresh(self, instance):
        """Refresh an instance from the database."""
        try:
            await self.session.refresh(instance)
        except Exception as e:
            logger.error(f"Error refreshing instance: {e}")
            raise


class UnitOfWorkFactory:
    """Factory for creating Unit of Work instances."""
    
    @staticmethod
    async def create(session: AsyncSession) -> AbstractUnitOfWork:
        """Create a new Unit of Work instance."""
        return SqlAlchemyUnitOfWork(session)


# Dependency function for FastAPI  
async def get_unit_of_work(session: AsyncSession) -> AbstractUnitOfWork:
    """Dependency function to provide Unit of Work instance."""
    return SqlAlchemyUnitOfWork(session)
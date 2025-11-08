from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.unit_of_work import SqlAlchemyUnitOfWork
from src.services.user_service import UserService
from src.services.analytics_service import AnalyticsService
from src.services.subscription_service import SubscriptionService
from src.services.api_key_service import APIKeyService
from src.services.auth_service import AuthService
from src.services.email import EmailService
from src.services.polar import polar_service


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency to provide UserService."""
    uow = SqlAlchemyUnitOfWork(db)
    email_service = EmailService(uow)
    return UserService(uow, email_service)


async def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    """Dependency to provide AnalyticsService."""
    uow = SqlAlchemyUnitOfWork(db)
    return AnalyticsService(uow)


async def get_subscription_service(db: AsyncSession = Depends(get_db)) -> SubscriptionService:
    """Dependency to provide SubscriptionService."""
    uow = SqlAlchemyUnitOfWork(db)
    return SubscriptionService(uow, polar_service)


async def get_api_key_service(db: AsyncSession = Depends(get_db)) -> APIKeyService:
    """Dependency to provide APIKeyService."""
    uow = SqlAlchemyUnitOfWork(db)
    return APIKeyService(uow)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency to provide AuthService."""
    uow = SqlAlchemyUnitOfWork(db)
    return AuthService(uow)
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.models import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String, nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Subscription fields
    subscription_tier = Column(String, nullable=True, default='free')  # 'free', 'starter', 'pro', or null
    subscription_status = Column(String, nullable=True, default='active')  # 'active', 'canceled', or null
    subscription_updated_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api_keys = relationship("APIKey", back_populates="user")
    emails = relationship("Email", back_populates="user")
    badge_tokens = relationship("BadgeToken", back_populates="user")

    @property
    def is_free_plan(self) -> bool:
        """Check if user is on the free plan."""
        return self.subscription_tier == 'free'

    @property
    def has_active_subscription(self) -> bool:
        """Check if user has an active subscription (including free plan)."""
        return self.subscription_status == 'active'

    def get_rate_limit_per_hour(self) -> int:
        """Get the rate limit per hour based on user's plan."""
        from src.core.config import settings
        
        if self.is_free_plan:
            return settings.FREE_PLAN_RATE_LIMIT_PER_HOUR
        else:
            return settings.PAID_PLAN_RATE_LIMIT_PER_HOUR

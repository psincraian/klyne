"""BadgeToken model for user count badge generation."""

import secrets

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.models import Base


class BadgeToken(Base):
    """Model for storing badge tokens that allow public access to user count badges."""

    __tablename__ = "badge_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="badge_tokens")

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token for badge access."""
        return secrets.token_urlsafe(32)

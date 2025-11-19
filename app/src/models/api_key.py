import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.models import Base
import secrets


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    package_name = Column(String, nullable=False, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    badge_public = Column(Boolean, default=False, nullable=False)
    badge_uuid = Column(UUID(as_uuid=True), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="api_keys")

    @classmethod
    def generate_key(cls) -> str:
        return f"klyne_{secrets.token_urlsafe(32)}"

    @classmethod
    def generate_badge_uuid(cls) -> uuid.UUID:
        """Generate a unique UUID for badge access."""
        return uuid.uuid4()

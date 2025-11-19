import uuid

from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.models import Base


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, unique=True)
    badge_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    api_key = relationship("APIKey", back_populates="badge")

    @classmethod
    def generate_uuid(cls) -> uuid.UUID:
        """Generate a unique UUID for badge access."""
        return uuid.uuid4()


from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.models import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    email_address = Column(String, nullable=False, index=True)
    email_type = Column(String, nullable=False, index=True)  # 'welcome', 'verification', 'password_reset'
    subject = Column(String, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, nullable=False, default='sent')  # 'sent', 'failed', 'pending'
    error_message = Column(Text, nullable=True)
    email_metadata = Column(JSON, nullable=True)  # Additional data like resend_id, template vars, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="emails")

    def __repr__(self):
        return f"<Email(id={self.id}, type={self.email_type}, to={self.email_address}, status={self.status})>"
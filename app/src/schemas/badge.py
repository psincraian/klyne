"""Pydantic schemas for badge token operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BadgeTokenBase(BaseModel):
    """Base schema for badge tokens."""

    pass


class BadgeTokenCreate(BadgeTokenBase):
    """Schema for creating a badge token."""

    pass


class BadgeTokenResponse(BadgeTokenBase):
    """Schema for badge token responses."""

    id: int
    user_id: int
    token: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BadgeTokenPublic(BaseModel):
    """Public schema for badge token (only shows token)."""

    token: str


class BadgeURLResponse(BaseModel):
    """Response schema for badge URL generation."""

    token: str
    badge_url: str
    markdown: str
    html: str

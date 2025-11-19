from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class BadgeBase(BaseModel):
    is_public: bool = False


class BadgeCreate(BadgeBase):
    api_key_id: int


class BadgeUpdate(BaseModel):
    is_public: bool


class BadgeResponse(BaseModel):
    id: int
    api_key_id: int
    badge_uuid: UUID
    is_public: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class BadgePublicResponse(BaseModel):
    """Public response for badge data (shown in badge SVG/JSON)."""
    package_name: str
    unique_users: int
    is_public: bool

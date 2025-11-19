from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class APIKeyBase(BaseModel):
    package_name: str = Field(
        ..., min_length=1, max_length=100, description="Package name to track"
    )


class APIKeyCreate(APIKeyBase):
    description: Optional[str] = None


class APIKeyResponse(APIKeyBase):
    id: int
    key: str
    user_id: int
    is_active: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyInDB(APIKeyResponse):
    pass


class APIKeyUpdate(BaseModel):
    """Schema for updating API key settings."""
    description: Optional[str] = None

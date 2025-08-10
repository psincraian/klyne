from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class APIKeyBase(BaseModel):
    package_name: str = Field(
        ..., min_length=1, max_length=100, description="Package name to track"
    )


class APIKeyCreate(APIKeyBase):
    pass


class APIKeyResponse(APIKeyBase):
    id: int
    key: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyInDB(APIKeyResponse):
    pass

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserInDB(UserBase):
    id: int
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: int
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VerificationRequest(BaseModel):
    token: str
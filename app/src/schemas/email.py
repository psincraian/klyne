from pydantic import BaseModel, EmailStr
from datetime import datetime


class EmailBase(BaseModel):
    email: EmailStr


class EmailCreate(EmailBase):
    pass


class EmailInDB(EmailBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
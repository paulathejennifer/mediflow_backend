from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime


def normalize_email(value: str) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return value


class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    gender: Optional[str] = None
    role: Optional[str] = "clinician"
    facility_id: Optional[int] = None
    is_active: Optional[bool] = True

    _normalize_email = validator("email", pre=True, allow_reuse=True)(normalize_email)


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    role: Optional[str] = None
    facility_id: Optional[int] = None
    is_active: Optional[bool] = None

    _normalize_email = validator("email", pre=True, allow_reuse=True)(normalize_email)


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    password_hash: str

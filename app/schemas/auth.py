from pydantic import BaseModel, EmailStr, validator
from typing import Optional


def normalize_email(value: str) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    _normalize_email = validator("email", pre=True, allow_reuse=True)(normalize_email)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    role: Optional[str] = "clinician"
    facility_id: Optional[int] = None

    _normalize_email = validator("email", pre=True, allow_reuse=True)(normalize_email)


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    role: str
    facility_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    _normalize_email = validator("email", pre=True, allow_reuse=True)(normalize_email)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr

    _normalize_email = validator("email", pre=True, allow_reuse=True)(normalize_email)


class VerifyCodeRequest(BaseModel):
    code: str
    email: Optional[EmailStr] = None

    _normalize_email = validator("email", pre=True, allow_reuse=True)(normalize_email)


class RefreshTokenRequest(BaseModel):
    refresh_token: str

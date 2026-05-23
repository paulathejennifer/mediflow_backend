from pydantic import BaseModel, EmailStr
from typing import Optional


class UserLogin(BaseModel):
    email: EmailStr
    password: str


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
    role: Optional[str] = "clinician"
    facility_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
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


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    code: str
    email: Optional[EmailStr] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str

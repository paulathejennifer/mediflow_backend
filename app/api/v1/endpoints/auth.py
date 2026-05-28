from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.auth_service import AuthService, get_auth_service
from app.services.audit_service import AuditService, create_audit_logger
from app.services.email_service import EmailService
from app.schemas.auth import (
    UserLogin,
    UserCreate,
    UserResponse,
    Token,
    PasswordChange,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    VerifyCodeRequest,
    RefreshTokenRequest,
)
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.models.email_verification_token import EmailVerificationToken
from app.enums import AuditAction

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user."""
    try:
        user = auth_service.create_user(user_data)

        # Log registration
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=user.id,
            action=AuditAction.CREATE.value,
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email, "role": user.role},
        )

        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login", response_model=Token)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Login user and return access token."""
    try:
        print(f"Login attempt for email: {login_data.email}")
        result = auth_service.login_user(login_data)
        print(f"Login successful for email: {login_data.email}")

        # Log login
        audit_logger = create_audit_logger(db)
        user = auth_service.get_user_by_email(login_data.email)
        if user:
            audit_logger.log_action(
                user_id=user.id,
                action=AuditAction.LOGIN.value,
                entity_type="user",
                entity_id=user.id,
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Change user password."""
    try:
        auth_service.update_user_password(
            current_user.id, password_data.current_password, password_data.new_password
        )

        # Log password change
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=current_user.id,
            details={"action": "password_change"},
        )

        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}",
        )


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Logout user (client-side token removal)."""
    # Log logout
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action=AuditAction.LOGOUT,
        entity_type="user",
        entity_id=current_user.id,
    )

    return {"message": "Logout successful"}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    """Request password reset email."""
    email = request.email.strip().lower()
    # Find user by email
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Don't reveal if user exists or not for security
        return {"message": "If the email exists, a password reset link has been sent"}

    # Generate reset token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    # Invalidate any existing tokens for this user
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()

    # Create new reset token
    reset_token = PasswordResetToken(
        user_id=user.id, token=token, expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()

    # Send email
    email_service = EmailService()
    await email_service.send_password_reset(
        email=user.email, token=token, user_name=user.first_name
    )

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using token."""
    # Find valid token
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == request.token,
            PasswordResetToken.used.is_(None),
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Get user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update password
    import bcrypt

    hashed_password = bcrypt.hashpw(
        request.new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    user.password_hash = hashed_password

    # Mark token as used
    reset_token.used = datetime.utcnow()

    db.commit()

    # Log password reset
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=user.id,
        action=AuditAction.UPDATE,
        entity_type="user",
        entity_id=user.id,
        details={"action": "password_reset"},
    )

    return {"message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email using token."""
    # Find valid token
    verification_token = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.token == request.token,
            EmailVerificationToken.verified.is_(None),
            EmailVerificationToken.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Get user
    user = db.query(User).filter(User.id == verification_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Mark token as verified
    verification_token.verified = datetime.utcnow()

    # Update user email if different
    if user.email != verification_token.email:
        user.email = verification_token.email

    db.commit()

    # Log verification
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=user.id,
        action=AuditAction.UPDATE,
        entity_type="user",
        entity_id=user.id,
        details={"action": "email_verified"},
    )

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest, db: Session = Depends(get_db)
):
    """Resend email verification."""
    email = request.email.strip().lower()
    # Find user by email
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Don't reveal if user exists or not for security
        return {"message": "If the email exists, a verification link has been sent"}

    # Generate verification token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)

    # Invalidate any existing tokens for this user
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id
    ).delete()

    # Create new verification token
    verification_token = EmailVerificationToken(
        user_id=user.id, token=token, email=user.email, expires_at=expires_at
    )
    db.add(verification_token)
    db.commit()

    # Send email
    email_service = EmailService()
    await email_service.send_email_verification(
        email=user.email, token=token, user_name=user.first_name
    )

    return {"message": "If the email exists, a verification link has been sent"}


@router.post("/verify-code")
def verify_code(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    """Verify a code (for 2FA or email verification)."""
    # This is a placeholder for code verification logic
    # In a real implementation, you would verify the code against stored codes
    # For now, we'll return a success message

    if request.email:
        email = request.email.strip().lower()
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Log verification attempt
            audit_logger = create_audit_logger(db)
            audit_logger.log_action(
                user_id=user.id,
                action=AuditAction.UPDATE,
                entity_type="user",
                entity_id=user.id,
                details={"action": "code_verification_attempt"},
            )

    return {"message": "Code verified successfully"}


@router.post("/refresh-token")
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token using refresh token."""
    try:
        result = auth_service.refresh_access_token(request.refresh_token)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}",
        )

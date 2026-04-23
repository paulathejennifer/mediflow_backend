from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.auth_service import AuthService, get_auth_service
from app.services.audit_service import AuditService, create_audit_logger
from app.schemas.auth import UserLogin, UserCreate, UserResponse, Token, PasswordChange
from app.models.user import User
from app.enums import AuditAction

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user."""
    try:
        user = auth_service.create_user(user_data)
        
        # Log registration
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=user.id,
            action=AuditAction.CREATE,
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email, "role": user.role}
        )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login user and return access token."""
    try:
        result = auth_service.login_user(login_data)
        
        # Log login
        audit_logger = create_audit_logger(db)
        user = auth_service.get_user_by_email(login_data.email)
        if user:
            audit_logger.log_action(
                user_id=user.id,
                action=AuditAction.LOGIN,
                entity_type="user",
                entity_id=user.id
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user

@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Change user password."""
    try:
        auth_service.update_user_password(
            current_user.id,
            password_data.current_password,
            password_data.new_password
        )
        
        # Log password change
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=current_user.id,
            details={"action": "password_change"}
        )
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}"
        )

@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user (client-side token removal)."""
    # Log logout
    audit_logger = create_audit_logger(db)
    audit_logger.log_action(
        user_id=current_user.id,
        action=AuditAction.LOGOUT,
        entity_type="user",
        entity_id=current_user.id
    )
    
    return {"message": "Logout successful"}

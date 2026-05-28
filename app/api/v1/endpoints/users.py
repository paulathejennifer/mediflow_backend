from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.utils.permissions import get_permission_checker
from app.utils.audit_utils import create_audit_logger
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.models.user import User
from app.models.facility import Facility
from app.services.auth_service import AuthService, get_auth_service
from app.enums import UserRole, AuditAction
from app.services.notification_service import get_notification_service

router = APIRouter()


@router.post("", response_model=UserResponse)
@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Create a new user (Admin only)."""
    permission_checker = get_permission_checker(current_user, db)

    # Check permissions
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin can create any user type
        pass
    elif current_user.role == UserRole.FACILITY_ADMIN:
        # Facility admin can only create clinicians and patients in their facility
        if user_data.role not in [UserRole.CLINICIAN.value, UserRole.PATIENT.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Facility admins can only create clinicians and patients",
            )

        if user_data.facility_id != current_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Facility admins can only create users in their facility",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create users"
        )

    try:
        user = auth_service.create_user(user_data)

        # Log creation
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.CREATE.value,
            entity_type="user",
            entity_id=user.id,
            details={
                "email": user.email,
                "role": user.role,
                "facility_id": user.facility_id,
            },
        )

        # Trigger Role-Based Notifications
        notif_service = get_notification_service(db)
        if user.role == UserRole.FACILITY_ADMIN.value:
            facility = db.query(Facility).filter(Facility.id == user.facility_id).first()
            notif_service.create_facility_admin_assigned_notification(user, facility)
        elif user.role == UserRole.CLINICIAN.value:
            facility = db.query(Facility).filter(Facility.id == user.facility_id).first()
            if facility:
                notif_service.create_clinician_created_notification(user, facility)

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.get("", response_model=List[UserResponse])
@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = Query(None),
    facility_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List users accessible to the current user."""
    query = db.query(User)

    # Apply role-based filtering
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin can see all users
        pass
    elif current_user.role == UserRole.FACILITY_ADMIN:
        # Facility admin can only see users in their facility
        query = query.filter(User.facility_id == current_user.facility_id)
    elif current_user.role == UserRole.CLINICIAN:
        # Clinicians can only see users in their facility
        query = query.filter(User.facility_id == current_user.facility_id)
    else:
        # Patients can only see themselves
        query = query.filter(User.id == current_user.id)

    # Apply filters
    if role:
        query = query.filter(User.role == role)

    if facility_id and current_user.role == UserRole.SUPER_ADMIN:
        query = query.filter(User.facility_id == facility_id)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user by ID."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_user_management(target_user_id=user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user details."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_user_management(target_user_id=user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    try:
        # Update fields
        update_data = user_update.dict(exclude_unset=True)

        # Facility admins can't change roles or facility assignments
        if current_user.role == UserRole.FACILITY_ADMIN:
            if "role" in update_data or "facility_id" in update_data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Facility admins cannot change user roles or facility assignments",
                )

        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        # Log update
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user.id,
            details=update_data,
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}",
        )


@router.delete("/{user_id}")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Deactivate user account."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_user_management(target_user_id=user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Cannot deactivate self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    try:
        auth_service.deactivate_user(user_id)

        # Log deactivation
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.DELETE.value,
            entity_type="user",
            entity_id=user.id,
            details={"action": "deactivate", "email": user.email, "role": user.role},
        )

        return {"message": "User deactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate user: {str(e)}",
        )


@router.delete("/{user_id}/hard")
def hard_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete user account (Super Admin only)."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can permanently delete users",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Cannot delete self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    try:
        # Delete associated audit logs first (they have NOT NULL constraint on user_id)
        from app.models.audit_log import AuditLog

        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()

        # Delete other related records
        from app.models.refresh_token import RefreshToken

        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()

        from app.models.password_reset_token import PasswordResetToken

        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id
        ).delete()

        from app.models.email_verification_token import EmailVerificationToken

        db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user_id
        ).delete()

        # Delete the user
        db.delete(user)
        db.commit()

        return {"message": "User permanently deleted"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )


@router.post("/{user_id}/activate")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Activate user account."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_user_management(target_user_id=user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    try:
        auth_service.activate_user(user_id)

        # Log activation
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user.id,
            details={"action": "activate", "email": user.email, "role": user.role},
        )

        return {"message": "User activated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate user: {str(e)}",
        )

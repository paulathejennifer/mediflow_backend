from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_same_facility
from app.utils.permissions import get_permission_checker
from app.utils.audit_utils import create_audit_logger
from app.schemas.facility import (
    FacilityCreate,
    FacilityUpdate,
    FacilityResponse,
    FacilitySummary,
)
from app.models.facility import Facility
from app.models.user import User
from app.enums import UserRole, AuditAction
from app.services.notification_service import get_notification_service
from app.services.facility_service import FacilityService

router = APIRouter()


@router.post("", response_model=FacilityResponse)
@router.post("/", response_model=FacilityResponse)
def create_facility(
    facility_data: FacilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new facility (Super Admin only)."""
    # Check permissions
    permission_checker = get_permission_checker(current_user, db)
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can create facilities",
        )

    try:
        facility_service = FacilityService(db)
        facility = facility_service.create_facility(facility_data, current_user.id)

        # Log creation
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.CREATE,
            entity_type="facility",
            entity_id=facility.id,
            details={"name": facility.name, "code": facility.facility_code},
        )

        # Notify Super Admins
        notif_service = get_notification_service(db)
        notif_service.create_facility_created_notification(facility, current_user.id)

        return facility
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create facility: {str(e)}",
        )


@router.get("", response_model=List[FacilitySummary])
@router.get("/", response_model=List[FacilitySummary])
def list_facilities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    county: Optional[str] = Query(None),
    facility_type: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List facilities with optional filters."""
    # PostgreSQL VARCHAR mismatch fix: compare to string literal
    query = db.query(Facility).filter(Facility.is_active == "true")

    # Apply filters
    if county:
        query = query.filter(Facility.county.ilike(f"%{county}%"))

    if facility_type:
        query = query.filter(Facility.type == facility_type)

    if level:
        query = query.filter(Facility.level == level)

    # Non-super admins can only see their own facility
    if current_user.role != UserRole.SUPER_ADMIN and current_user.facility_id:
        query = query.filter(Facility.id == current_user.facility_id)

    facilities = query.offset(skip).limit(limit).all()

    return [
        FacilitySummary(
            id=f.id,
            name=f.name,
            facility_code=f.facility_code,
            type=f.type,
            level=f.level,
            county=f.county,
        )
        for f in facilities
    ]


@router.get("/{facility_id}", response_model=FacilityResponse)
def get_facility(
    facility_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get facility by ID."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_facility_access(facility_id)

    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found"
        )

    return facility


@router.put("/{facility_id}", response_model=FacilityResponse)
def update_facility(
    facility_id: int,
    facility_update: FacilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update facility details."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_facility_access(facility_id)

    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found"
        )

    try:
        # Update fields
        update_data = facility_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(facility, field, value)

        db.commit()
        db.refresh(facility)

        # Log update
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="facility",
            entity_id=facility.id,
            details=update_data,
        )

        return facility
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update facility: {str(e)}",
        )


@router.delete("/{facility_id}")
def deactivate_facility(
    facility_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate facility (Super Admin only)."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can deactivate facilities",
        )

    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found"
        )

    try:
        facility.is_active = "false"
        db.commit()

        # Log deactivation
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.DELETE,
            entity_type="facility",
            entity_id=facility.id,
            details={"action": "deactivate", "name": facility.name},
        )

        # Notify Super Admins
        notif_service = get_notification_service(db)
        # Passing False as old_status for notification logic
        notif_service.create_facility_status_changed_notification(facility, True, "Manual deactivation")

        return {"message": "Facility deactivated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate facility: {str(e)}",
        )

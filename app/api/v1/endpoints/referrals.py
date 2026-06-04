from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.utils.permissions import get_permission_checker
from app.utils.audit_utils import create_audit_logger
from app.schemas.referral import (
    ReferralCreate,
    ReferralUpdate,
    ReferralResponse,
    ReferralSummary,
    ReferralWithDetails,
)
from app.models.referral import Referral
from app.models.patient import Patient
from app.models.facility import Facility
from app.models.user import User
from app.enums import UserRole, AuditAction, ReferralStatus, Priority
from app.services.notification_service import get_notification_service
from sqlalchemy import func

router = APIRouter(redirect_slashes=True)


@router.post("", response_model=ReferralResponse)
@router.post("/", response_model=ReferralResponse)
async def create_referral(
    referral_data: ReferralCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new referral."""
    permission_checker = get_permission_checker(current_user, db)

    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.FACILITY_ADMIN, UserRole.CLINICIAN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role")

    if not current_user.facility_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must have a facility")

    try:
        patient = db.query(Patient).filter(Patient.id == referral_data.patient_id).first()
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        permission_checker.check_patient_access(referral_data.patient_id)

        referral = Referral(
            patient_id=referral_data.patient_id,
            from_facility_id=current_user.facility_id,
            to_facility_id=referral_data.to_facility_id,
            created_by=current_user.id,
            priority=referral_data.priority,
            reason_for_referral=referral_data.reason_for_referral,
            clinical_notes=referral_data.clinical_notes,
            status=ReferralStatus.DRAFT,
        )

        db.add(referral)
        db.commit()
        db.refresh(referral)
        return referral
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[ReferralSummary])
@router.get("/", response_model=List[ReferralSummary])
def list_referrals(
    skip: int = Query(0),
    limit: int = Query(100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Referral)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter((Referral.from_facility_id == current_user.facility_id) | (Referral.to_facility_id == current_user.facility_id))
    
    if status:
        query = query.filter(Referral.status == status)
        
    referrals = query.order_by(Referral.created_at.desc()).offset(skip).limit(limit).all()
    return [ReferralSummary(
        id=r.id,
        patient_name=f"{r.patient.first_name} {r.patient.last_name}",
        from_facility_name=r.from_facility.name,
        to_facility_name=r.to_facility.name,
        status=r.status,
        priority=r.priority,
        created_at=r.created_at
    ) for r in referrals]

@router.get("/{referral_id}", response_model=ReferralWithDetails)
def get_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_permission_checker(current_user, db).check_referral_access(referral_id)
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    return referral

@router.put("/{referral_id}", response_model=ReferralResponse)
def update_referral(
    referral_id: int,
    referral_update: ReferralUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_permission_checker(current_user, db).check_referral_access(referral_id)
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    for field, value in referral_update.dict(exclude_unset=True).items():
        setattr(referral, field, value)
    
    db.commit()
    db.refresh(referral)
    return referral

@router.post("/{referral_id}/submit")
@router.post("/{referral_id}/submit/")
async def submit_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    referral.status = ReferralStatus.SUBMITTED
    referral.submitted_at = func.now()
    db.commit()
    
    get_notification_service(db).create_incoming_referral_notification(referral)
    return {"message": "Referral submitted"}

@router.post("/{referral_id}/accept")
@router.post("/{referral_id}/accept/", response_model=ReferralResponse)
async def accept_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a submitted referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.status not in [ReferralStatus.SUBMITTED, ReferralStatus.PENDING]:
        raise HTTPException(status_code=400, detail=f"Invalid status: {referral.status}")

    if current_user.facility_id != referral.to_facility_id:
        raise HTTPException(status_code=403, detail="Only receiving facility can accept")

    try:
        referral.status = ReferralStatus.ACCEPTED
        referral.accepted_at = func.now()
        referral.accepted_by = current_user.id
        db.commit()
        db.refresh(referral)

        get_notification_service(db).create_referral_status_notification(referral)
        return referral
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{referral_id}/reject")
@router.post("/{referral_id}/reject/", response_model=ReferralResponse)
async def reject_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a submitted referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.status not in [ReferralStatus.SUBMITTED, ReferralStatus.PENDING]:
        raise HTTPException(status_code=400, detail="Referral cannot be rejected in this state")

    try:
        referral.status = ReferralStatus.REJECTED
        referral.rejected_at = func.now()
        referral.rejected_by = current_user.id
        db.commit()
        db.refresh(referral)

        get_notification_service(db).create_referral_status_notification(referral)
        return referral
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

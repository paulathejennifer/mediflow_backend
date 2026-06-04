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

# redirect_slashes=True handles the /accept vs /accept/ issue automatically
router = APIRouter(redirect_slashes=True)

@router.post("", response_model=ReferralResponse)
@router.post("/", response_model=ReferralResponse)
async def create_referral(
    referral_data: ReferralCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission_checker = get_permission_checker(current_user, db)
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.FACILITY_ADMIN, UserRole.CLINICIAN]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
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

@router.get("", response_model=List[ReferralSummary])
@router.get("/", response_model=List[ReferralSummary])
def list_referrals(
    skip: int = Query(0),
    limit: int = Query(100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Referral).options(
        joinedload(Referral.patient),
        joinedload(Referral.from_facility),
        joinedload(Referral.to_facility)
    )
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter((Referral.from_facility_id == current_user.facility_id) | (Referral.to_facility_id == current_user.facility_id))
    if status:
        query = query.filter(Referral.status == status)
    return query.order_by(Referral.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{referral_id}", response_model=ReferralWithDetails)
@router.get("/{referral_id}/", response_model=ReferralWithDetails)
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

@router.post("/{referral_id}/submit")
@router.post("/{referral_id}/submit/")
async def submit_referral(referral_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    referral.status = ReferralStatus.SUBMITTED
    db.commit()
    get_notification_service(db).create_incoming_referral_notification(referral)
    return {"message": "Submitted"}

@router.post("/{referral_id}/accept")
@router.post("/{referral_id}/accept/")
async def accept_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    
    if current_user.facility_id != referral.to_facility_id:
        raise HTTPException(status_code=403, detail="Unauthorized facility")

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
@router.post("/{referral_id}/reject/")
async def reject_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

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

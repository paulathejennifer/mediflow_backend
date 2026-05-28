from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
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

router = APIRouter()


@router.post("", response_model=ReferralResponse)
@router.post("/", response_model=ReferralResponse)
async def create_referral(
    referral_data: ReferralCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new referral."""
    permission_checker = get_permission_checker(current_user, db)

    if current_user.role not in [
        UserRole.SUPER_ADMIN,
        UserRole.FACILITY_ADMIN,
        UserRole.CLINICIAN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinicians and admins can create referrals",
        )

    if not current_user.facility_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be assigned to a facility to create referrals",
        )

    try:
        # Verify patient exists and is accessible
        patient = (
            db.query(Patient).filter(Patient.id == referral_data.patient_id).first()
        )
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )

        permission_checker.check_patient_access(referral_data.patient_id)

        # Verify to facility exists
        to_facility = (
            db.query(Facility)
            .filter(Facility.id == referral_data.to_facility_id)
            .first()
        )
        if not to_facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destination facility not found",
            )

        if not to_facility.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination facility is not active",
            )

        # Create referral
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

        # Log creation
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.CREATE.value,
            entity_type="referral",
            entity_id=referral.id,
            details={
                "patient_id": referral.patient_id,
                "from_facility_id": referral.from_facility_id,
                "to_facility_id": referral.to_facility_id,
                "priority": referral.priority,
            },
        )

        # SA001: Trigger notification for urgent/emergency drafts
        # While clinicians usually check the dashboard, emergency drafts
        # require immediate visibility.
        if referral.priority == Priority.EMERGENCY.value or referral.priority == "emergency":
            get_notification_service(db).create_incoming_referral_notification(referral)

        return referral

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create referral: {str(e)}",
        )


@router.get("", response_model=List[ReferralSummary])
@router.get("/", response_model=List[ReferralSummary])
def list_referrals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List referrals accessible to the current user."""
    query = db.query(Referral)

    # Filter by user's facility (sender or receiver)
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(
            (Referral.from_facility_id == current_user.facility_id)
            | (Referral.to_facility_id == current_user.facility_id)
        )

    # Apply filters
    if status:
        query = query.filter(Referral.status == status)

    if priority:
        query = query.filter(Referral.priority == priority)

    if patient_id:
        query = query.filter(Referral.patient_id == patient_id)

    referrals = (
        query.order_by(Referral.created_at.desc()).offset(skip).limit(limit).all()
    )

    # Create summaries with related data
    result = []
    for referral in referrals:
        patient = db.query(Patient).filter(Patient.id == referral.patient_id).first()
        from_facility = (
            db.query(Facility).filter(Facility.id == referral.from_facility_id).first()
        )
        to_facility = (
            db.query(Facility).filter(Facility.id == referral.to_facility_id).first()
        )

        summary = ReferralSummary(
            id=referral.id,
            patient_name=f"{patient.first_name} {patient.last_name}"
            if patient
            else "Unknown",
            from_facility_name=from_facility.name if from_facility else "Unknown",
            to_facility_name=to_facility.name if to_facility else "Unknown",
            status=referral.status,
            priority=referral.priority,
            created_at=referral.created_at,
        )
        result.append(summary)

    return result


@router.get("/{referral_id}", response_model=ReferralWithDetails)
def get_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get referral by ID with full details."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
        )

    # Load related data
    patient = db.query(Patient).filter(Patient.id == referral.patient_id).first()
    from_facility = (
        db.query(Facility).filter(Facility.id == referral.from_facility_id).first()
    )
    to_facility = (
        db.query(Facility).filter(Facility.id == referral.to_facility_id).first()
    )
    creator = db.query(User).filter(User.id == referral.created_by).first()

    # Load documents and voice notes
    documents = []
    voice_notes = []

    referral_with_details = ReferralWithDetails(
        **referral.__dict__,
        patient={
            "id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "date_of_birth": patient.date_of_birth,
            "gender": patient.gender,
        }
        if patient
        else None,
        from_facility={
            "id": from_facility.id,
            "name": from_facility.name,
            "facility_code": from_facility.facility_code,
        }
        if from_facility
        else None,
        to_facility={
            "id": to_facility.id,
            "name": to_facility.name,
            "facility_code": to_facility.facility_code,
        }
        if to_facility
        else None,
        creator={
            "id": creator.id,
            "first_name": creator.first_name,
            "last_name": creator.last_name,
        }
        if creator
        else None,
        documents=documents,
        voice_notes=voice_notes,
    )

    return referral_with_details


@router.put("/{referral_id}", response_model=ReferralResponse)
def update_referral(
    referral_id: int,
    referral_update: ReferralUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update referral details."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
        )

    try:
        # Update fields
        update_data = referral_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(referral, field, value)

        db.commit()
        db.refresh(referral)

        # Log update
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="referral",
            entity_id=referral.id,
            details=update_data,
        )

        return referral

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update referral: {str(e)}",
        )


@router.post("/{referral_id}/submit")
async def submit_referral(
    referral_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a draft referral."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_referral_access(referral_id)

    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
        )

    if referral.status != ReferralStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft referrals can be submitted",
        )

    if current_user.facility_id != referral.from_facility_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sender facility can submit referrals",
        )

    try:
        referral.status = ReferralStatus.SUBMITTED
        db.commit()

        # Log submission
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            entity_type="referral",
            entity_id=referral.id,
            details={"action": "submit", "status": ReferralStatus.SUBMITTED},
        )

        # FA001: Notify receiving facility clinicians of new incoming referral
        notif_service = get_notification_service(db)
        notif_service.create_incoming_referral_notification(referral)

        return {"message": "Referral submitted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit referral: {str(e)}",
        )

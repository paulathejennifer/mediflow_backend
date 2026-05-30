from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.utils.permissions import get_permission_checker
from app.utils.audit_utils import create_audit_logger
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientWithIdentifiers,
)
from app.models.patient import Patient
from app.models.patient_identifier import PatientIdentifier
from app.models.facility import Facility
from app.models.user import User
from app.services.mrn_service import MRNService
from app.enums import UserRole, AuditAction

router = APIRouter()


@router.post("", response_model=PatientWithIdentifiers)
@router.post("/", response_model=PatientWithIdentifiers)
def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new patient and assign MRN."""
    # Check permissions
    permission_checker = get_permission_checker(current_user, db)

    if current_user.role not in [
        UserRole.SUPER_ADMIN,
        UserRole.FACILITY_ADMIN,
        UserRole.CLINICIAN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinicians and admins can create patients",
        )

    if not current_user.facility_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be assigned to a facility to create patients",
        )

    try:
        # Get facility
        facility = (
            db.query(Facility).filter(Facility.id == current_user.facility_id).first()
        )
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found"
            )

        # Create patient with MRN
        mrn_service = MRNService(db)
        patient, identifier = mrn_service.create_patient_with_mrn(
            patient_data.dict(), current_user.facility_id, facility.facility_code
        )

        # Refresh identifier to load facility relationship
        db.refresh(identifier)

        # Log creation
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.CREATE.value,
            entity_type="patient",
            entity_id=patient.id,
            details={
                "name": f"{patient.first_name} {patient.last_name}",
                "mrn": identifier.mrn,
                "facility_id": current_user.facility_id,
            },
        )

        # Add facility info to identifier for response
        identifier.facility_name = facility.name
        identifier.facility_code = facility.facility_code

        # Return patient with identifiers
        patient.identifiers = [identifier]
        return patient

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create patient: {str(e)}",
        )


@router.get("", response_model=List[PatientWithIdentifiers])
@router.get("/", response_model=List[PatientWithIdentifiers])
def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List patients accessible to the current user."""
    permission_checker = get_permission_checker(current_user, db)

    # Super admin can see all patients, others see facility-specific
    if current_user.role == UserRole.SUPER_ADMIN:
        query = db.query(Patient).options(joinedload(Patient.identifiers).joinedload(PatientIdentifier.facility))
        facility = None
    else:
        # Get facility
        facility = (
            db.query(Facility).filter(Facility.id == current_user.facility_id).first()
        )
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found"
            )

        # Base query - get patients from user's facility
        query = (
            db.query(Patient)
            .join(PatientIdentifier)
            .filter(PatientIdentifier.facility_id == current_user.facility_id)
            .options(joinedload(Patient.identifiers).joinedload(PatientIdentifier.facility))
        )

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Patient.first_name.ilike(search_term))
            | (Patient.last_name.ilike(search_term))
            | (Patient.phone.ilike(search_term))
        )

    patients = query.offset(skip).limit(limit).all()

    # Load identifiers for each patient
    result = []
    for patient in patients:
        # Filter identifiers based on role (already loaded via joinedload)
        identifiers = [
            i for i in patient.identifiers 
            if current_user.role == UserRole.SUPER_ADMIN or i.facility_id == current_user.facility_id
        ]

        # Populate facility info
        for identifier in identifiers:
            if identifier.facility:
                identifier.facility_name = identifier.facility.name
                identifier.facility_code = identifier.facility.facility_code

        patient.identifiers = identifiers
        result.append(patient)

    return result


@router.get("/{patient_id}", response_model=PatientWithIdentifiers)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get patient by ID."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_patient_access(patient_id)

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    # Get identifiers from user's facility
    identifiers = (
        db.query(PatientIdentifier)
        .filter(
            PatientIdentifier.patient_id == patient_id,
            PatientIdentifier.facility_id == current_user.facility_id,
        )
        .all()
    )

    patient.identifiers = identifiers
    return patient


@router.put("/{patient_id}", response_model=PatientWithIdentifiers)
def update_patient(
    patient_id: int,
    patient_update: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update patient details."""
    permission_checker = get_permission_checker(current_user, db)
    permission_checker.check_patient_access(patient_id)

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    try:
        # Update fields
        update_data = patient_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(patient, field, value)

        db.commit()
        db.refresh(patient)

        # Log update
        audit_logger = create_audit_logger(db)
        # Convert date objects to strings for JSON serialization
        audit_details = {}
        for key, value in update_data.items():
            if hasattr(value, "isoformat"):
                audit_details[key] = value.isoformat()
            else:
                audit_details[key] = value
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE.value,
            entity_type="patient",
            entity_id=patient.id,
            details=audit_details,
        )

        # Get identifiers
        identifiers = (
            db.query(PatientIdentifier)
            .filter(
                PatientIdentifier.patient_id == patient_id,
                PatientIdentifier.facility_id == current_user.facility_id,
            )
            .all()
        )

        patient.identifiers = identifiers
        return patient

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update patient: {str(e)}",
        )


@router.get("/mrn/{mrn}", response_model=PatientWithIdentifiers)
def get_patient_by_mrn(
    mrn: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get patient by MRN."""
    if not current_user.facility_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be assigned to a facility",
        )

    try:
        mrn_service = MRNService(db)
        patient = mrn_service.get_patient_by_mrn(current_user.facility_id, mrn)

        # Get identifiers
        identifiers = (
            db.query(PatientIdentifier)
            .filter(
                PatientIdentifier.patient_id == patient.id,
                PatientIdentifier.facility_id == current_user.facility_id,
            )
            .all()
        )

        patient.identifiers = identifiers
        return patient

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient: {str(e)}",
        )


@router.delete("/{patient_id}/hard")
def hard_delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a patient and all associated records (Super Admin only)."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can permanently delete patients",
        )

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    try:
        # 1. Clean up identifiers
        db.query(PatientIdentifier).filter(PatientIdentifier.patient_id == patient_id).delete(synchronize_session=False)

        # 2. Clean up Referrals and their dependencies
        from app.models.referral import Referral
        from app.models.referral_document import ReferralDocument
        from app.models.voice_note import VoiceNote

        referral_ids = [
            r.id for r in db.query(Referral.id).filter(Referral.patient_id == patient_id).all()
        ]

        if referral_ids:
            db.query(ReferralDocument).filter(ReferralDocument.referral_id.in_(referral_ids)).delete(synchronize_session=False)
            db.query(VoiceNote).filter(VoiceNote.referral_id.in_(referral_ids)).delete(synchronize_session=False)
            db.query(Referral).filter(Referral.id.in_(referral_ids)).delete(synchronize_session=False)

        # 3. Delete the patient record
        db.delete(patient)
        db.commit()

        # Log deletion
        audit_logger = create_audit_logger(db)
        audit_logger.log_action(
            user_id=current_user.id,
            action=AuditAction.DELETE.value,
            entity_type="patient",
            entity_id=patient_id,
            details={"name": f"{patient.first_name} {patient.last_name}"},
        )

        return {"message": "Patient and all associated records permanently deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete patient: {str(e)}",
        )

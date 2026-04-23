"""
Patient Service for Mediflow System

This service handles patient-related business logic including:
- Patient creation and management
- MRN assignment
- Patient-facility relationships
- Patient search and filtering
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from app.models.patient import Patient
from app.models.patient_identifier import PatientIdentifier
from app.models.facility import Facility
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.mrn_service import MRNService
from typing import List, Optional, Dict, Any

class PatientService:
    """Service for patient management operations."""
    
    def __init__(self, db: Session):
        self.db = db

    def create_patient(self, patient_data: PatientCreate, facility_id: int, creator_id: int) -> tuple[Patient, PatientIdentifier]:
        """
        Create a new patient with MRN assignment.
        
        Args:
            patient_data: Patient creation data
            facility_id: Facility ID where patient is being created
            creator_id: ID of user creating this patient
            
        Returns:
            Tuple of (Patient, PatientIdentifier)
        """
        # Get facility for MRN generation
        facility = self.db.query(Facility).filter(Facility.id == facility_id).first()
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )
        
        # Create patient with MRN
        mrn_service = MRNService(self.db)
        patient, identifier = mrn_service.create_patient_with_mrn(
            patient_data.dict(),
            facility_id,
            facility.facility_code
        )
        
        return patient, identifier

    def get_patient_by_id(self, patient_id: int) -> Optional[Patient]:
        """Get patient by ID."""
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

    def get_patient_by_mrn(self, facility_id: int, mrn: str) -> Optional[Patient]:
        """
        Get patient by MRN within a specific facility.
        
        Args:
            facility_id: Facility ID
            mrn: MRN to search for
            
        Returns:
            Patient object if found
        """
        try:
            mrn_service = MRNService(self.db)
            return mrn_service.get_patient_by_mrn(facility_id, mrn)
        except ValueError:
            return None

    def update_patient(self, patient_id: int, patient_update: PatientUpdate, updater_id: int) -> Patient:
        """
        Update patient information.
        
        Args:
            patient_id: ID of patient to update
            patient_update: Update data
            updater_id: ID of user performing update
            
        Returns:
            Updated patient object
        """
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        update_data = patient_update.dict(exclude_unset=True)
        
        # Apply updates
        for field, value in update_data.items():
            setattr(patient, field, value)
        
        self.db.commit()
        self.db.refresh(patient)
        
        return patient

    def get_patient_identifiers(self, patient_id: int) -> List[PatientIdentifier]:
        """
        Get all MRNs for a patient across facilities.
        
        Args:
            patient_id: Patient ID
            
        Returns:
            List of patient identifiers
        """
        return (
            self.db.query(PatientIdentifier)
            .filter(PatientIdentifier.patient_id == patient_id)
            .all()
        )

    def get_facility_patients(self, facility_id: int, skip: int = 0, limit: int = 100, 
                            search: Optional[str] = None) -> List[Patient]:
        """
        Get patients in a specific facility.
        
        Args:
            facility_id: Facility ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Optional search term
            
        Returns:
            List of patients in the facility
        """
        query = (
            self.db.query(Patient)
            .join(PatientIdentifier)
            .filter(PatientIdentifier.facility_id == facility_id)
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Patient.first_name.ilike(search_term),
                    Patient.last_name.ilike(search_term),
                    Patient.phone.ilike(search_term)
                )
            )
        
        return query.offset(skip).limit(limit).all()

    def search_patients(self, facility_id: int, query: str, limit: int = 20) -> List[Patient]:
        """
        Search patients by name, phone, or MRN.
        
        Args:
            facility_id: Facility ID to search within
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching patients
        """
        search_term = f"%{query}%"
        
        return (
            self.db.query(Patient)
            .join(PatientIdentifier)
            .filter(
                and_(
                    PatientIdentifier.facility_id == facility_id,
                    or_(
                        Patient.first_name.ilike(search_term),
                        Patient.last_name.ilike(search_term),
                        Patient.phone.ilike(search_term),
                        PatientIdentifier.mrn.ilike(search_term)
                    )
                )
            )
            .limit(limit)
            .all()
        )

    def get_patient_summary(self, patient_id: int, facility_id: int) -> Dict[str, Any]:
        """
        Get comprehensive patient summary for a facility.
        
        Args:
            patient_id: Patient ID
            facility_id: Facility ID requesting the summary
            
        Returns:
            Dictionary with patient summary
        """
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Get patient's MRN for this facility
        identifier = (
            self.db.query(PatientIdentifier)
            .filter(
                and_(
                    PatientIdentifier.patient_id == patient_id,
                    PatientIdentifier.facility_id == facility_id
                )
            )
            .first()
        )
        
        if not identifier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found in this facility"
            )
        
        # Get referral statistics
        from app.models.referral import Referral
        total_referrals = self.db.query(Referral).filter(Referral.patient_id == patient_id).count()
        
        # Get recent referrals
        recent_referrals = (
            self.db.query(Referral)
            .filter(Referral.patient_id == patient_id)
            .order_by(Referral.created_at.desc())
            .limit(5)
            .all()
        )
        
        return {
            "patient_info": {
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "date_of_birth": patient.date_of_birth,
                "gender": patient.gender,
                "phone": patient.phone,
                "email": patient.email,
                "allergies": patient.allergies,
                "medications": patient.medications,
                "chronic_conditions": patient.chronic_conditions
            },
            "facility_info": {
                "mrn": identifier.mrn,
                "facility_id": facility_id,
                "created_at": identifier.created_at
            },
            "referral_stats": {
                "total_referrals": total_referrals,
                "recent_referrals": [
                    {
                        "id": ref.id,
                        "status": ref.status,
                        "priority": ref.priority,
                        "created_at": ref.created_at,
                        "from_facility_id": ref.from_facility_id,
                        "to_facility_id": ref.to_facility_id
                    }
                    for ref in recent_referrals
                ]
            }
        }

    def merge_patients(self, primary_patient_id: int, duplicate_patient_id: int, merger_id: int) -> Patient:
        """
        Merge duplicate patient records.
        
        Args:
            primary_patient_id: ID of patient to keep
            duplicate_patient_id: ID of patient to merge into primary
            merger_id: ID of user performing merge
            
        Returns:
            Updated primary patient
        """
        primary_patient = self.get_patient_by_id(primary_patient_id)
        duplicate_patient = self.get_patient_by_id(duplicate_patient_id)
        
        if not primary_patient or not duplicate_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both patients not found"
            )
        
        # Move all identifiers from duplicate to primary
        duplicate_identifiers = (
            self.db.query(PatientIdentifier)
            .filter(PatientIdentifier.patient_id == duplicate_patient_id)
            .all()
        )
        
        for identifier in duplicate_identifiers:
            identifier.patient_id = primary_patient_id
        
        # Update referrals to point to primary patient
        from app.models.referral import Referral
        self.db.query(Referral).filter(Referral.patient_id == duplicate_patient_id).update(
            {"patient_id": primary_patient_id}
        )
        
        # Delete duplicate patient
        self.db.delete(duplicate_patient)
        self.db.commit()
        
        return primary_patient

    def get_patient_demographics(self, facility_id: int) -> Dict[str, Any]:
        """
        Get demographic statistics for patients in a facility.
        
        Args:
            facility_id: Facility ID
            
        Returns:
            Dictionary with demographic statistics
        """
        # Get all patients in facility
        patients = self.get_facility_patients(facility_id, limit=10000)  # Large limit for stats
        
        total_patients = len(patients)
        
        if total_patients == 0:
            return {
                "total_patients": 0,
                "gender_breakdown": {},
                "age_distribution": {},
                "allergy_prevalence": 0,
                "medication_prevalence": 0
            }
        
        # Gender breakdown
        gender_counts = {}
        for patient in patients:
            gender_counts[patient.gender] = gender_counts.get(patient.gender, 0) + 1
        
        # Age distribution (simplified)
        from datetime import datetime
        current_year = datetime.now().year
        
        age_groups = {
            "0-17": 0,
            "18-30": 0,
            "31-50": 0,
            "51-65": 0,
            "65+": 0
        }
        
        allergies_count = 0
        medications_count = 0
        
        for patient in patients:
            # Age calculation
            if patient.date_of_birth:
                age = current_year - patient.date_of_birth.year
                if age <= 17:
                    age_groups["0-17"] += 1
                elif age <= 30:
                    age_groups["18-30"] += 1
                elif age <= 50:
                    age_groups["31-50"] += 1
                elif age <= 65:
                    age_groups["51-65"] += 1
                else:
                    age_groups["65+"] += 1
            
            # Allergies and medications
            if patient.allergies and patient.allergies.strip():
                allergies_count += 1
            
            if patient.medications and patient.medications.strip():
                medications_count += 1
        
        return {
            "total_patients": total_patients,
            "gender_breakdown": gender_counts,
            "age_distribution": age_groups,
            "allergy_prevalence": (allergies_count / total_patients) * 100,
            "medication_prevalence": (medications_count / total_patients) * 100
        }

def get_patient_service(db: Session) -> PatientService:
    """Get patient service instance."""
    return PatientService(db)

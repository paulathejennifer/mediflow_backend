from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.models.facility import Facility
from app.models.facility_counter import FacilityCounter
from app.models.patient import Patient
from app.models.patient_identifier import PatientIdentifier
from typing import Tuple

class MRNService:
    def __init__(self, db: Session):
        self.db = db

    def generate_mrn(self, facility_id: int, facility_code: str) -> str:
        """
        Generate a unique MRN with concurrency safety using row locking.
        
        Args:
            facility_id: The ID of the facility
            facility_code: The facility code (e.g., "KNRH")
            
        Returns:
            A unique MRN string (e.g., "KNRH-00001")
            
        Raises:
            Exception: If database operation fails
        """
        try:
            # Method 1: Using SELECT FOR UPDATE (simpler, good for MVP)
            counter = (
                self.db.query(FacilityCounter)
                .filter(FacilityCounter.facility_id == facility_id)
                .with_for_update()
                .first()
            )

            # If no counter exists, create it
            if not counter:
                counter = FacilityCounter(
                    facility_id=facility_id,
                    last_patient_number=0
                )
                self.db.add(counter)
                self.db.flush()  # Ensure it exists in DB before locking again

            # Increment safely
            counter.last_patient_number += 1
            new_number = counter.last_patient_number

            # Format MRN with zero-padding
            mrn = f"{facility_code}-{str(new_number).zfill(5)}"

            return mrn

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to generate MRN: {str(e)}")

    def generate_mrn_atomic(self, facility_id: int, facility_code: str) -> str:
        """
        Alternative atomic method using UPDATE...RETURNING.
        This is more performant for high concurrency scenarios.
        
        Args:
            facility_id: The ID of the facility
            facility_code: The facility code (e.g., "KNRH")
            
        Returns:
            A unique MRN string (e.g., "KNRH-00001")
        """
        try:
            # First ensure counter exists
            counter_exists = (
                self.db.query(FacilityCounter)
                .filter(FacilityCounter.facility_id == facility_id)
                .first()
            )
            
            if not counter_exists:
                # Create counter atomically
                counter = FacilityCounter(
                    facility_id=facility_id,
                    last_patient_number=0
                )
                self.db.add(counter)
                self.db.flush()

            # Atomic update and get new number
            result = self.db.execute(
                update(FacilityCounter)
                .where(FacilityCounter.facility_id == facility_id)
                .values(last_patient_number=FacilityCounter.last_patient_number + 1)
                .returning(FacilityCounter.last_patient_number)
            )
            
            new_number = result.scalar()
            mrn = f"{facility_code}-{str(new_number).zfill(5)}"
            
            return mrn

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to generate MRN atomically: {str(e)}")

    def create_patient_with_mrn(
        self, 
        patient_data: dict, 
        facility_id: int,
        facility_code: str,
        use_atomic: bool = False
    ) -> Tuple[Patient, PatientIdentifier]:
        """
        Create a patient and generate MRN in a single transaction.
        
        Args:
            patient_data: Dictionary with patient information
            facility_id: The ID of the facility
            facility_code: The facility code
            use_atomic: Whether to use atomic MRN generation
            
        Returns:
            Tuple of (Patient, PatientIdentifier)
        """
        try:
            # Generate MRN
            if use_atomic:
                mrn = self.generate_mrn_atomic(facility_id, facility_code)
            else:
                mrn = self.generate_mrn(facility_id, facility_code)

            # Create patient
            patient = Patient(
                first_name=patient_data["first_name"],
                last_name=patient_data["last_name"],
                date_of_birth=patient_data["date_of_birth"],
                gender=patient_data["gender"],
                phone=patient_data.get("phone"),
                email=patient_data.get("email"),
                address=patient_data.get("address"),
                emergency_contact_name=patient_data.get("emergency_contact_name"),
                emergency_contact_phone=patient_data.get("emergency_contact_phone"),
                medical_history=patient_data.get("medical_history"),
                allergies=patient_data.get("allergies"),
                medications=patient_data.get("medications"),
                chronic_conditions=patient_data.get("chronic_conditions"),
                facility_id=facility_id
            )

            self.db.add(patient)
            self.db.flush()  # Get patient.id

            # Create patient identifier
            identifier = PatientIdentifier(
                patient_id=patient.id,
                identifier_type="MRN",
                identifier_value=mrn,
                facility_id=facility_id,
                is_primary=True,
                mrn=mrn
            )

            self.db.add(identifier)
            self.db.commit()

            return patient, identifier

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create patient with MRN: {str(e)}")

    def validate_mrn_format(self, mrn: str) -> bool:
        """
        Validate MRN format (e.g., "KNRH-00001").
        
        Args:
            mrn: The MRN string to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        import re
        
        # Pattern: FACILITYCODE-5digits
        pattern = r'^[A-Z]+-\d{5}$'
        return bool(re.match(pattern, mrn))

    def parse_mrn(self, mrn: str) -> Tuple[str, int]:
        """
        Parse MRN to extract facility code and patient number.
        
        Args:
            mrn: The MRN string to parse
            
        Returns:
            Tuple of (facility_code, patient_number)
            
        Raises:
            ValueError: If MRN format is invalid
        """
        if not self.validate_mrn_format(mrn):
            raise ValueError(f"Invalid MRN format: {mrn}")
        
        facility_code, patient_number_str = mrn.split('-')
        patient_number = int(patient_number_str)
        
        return facility_code, patient_number

    def get_patient_by_mrn(self, facility_id: int, mrn: str) -> Patient:
        """
        Get patient by MRN within a specific facility.
        
        Args:
            facility_id: The facility ID
            mrn: The MRN to search for
            
        Returns:
            Patient object
            
        Raises:
            ValueError: If patient not found
        """
        identifier = (
            self.db.query(PatientIdentifier)
            .filter(
                PatientIdentifier.facility_id == facility_id,
                PatientIdentifier.mrn == mrn
            )
            .first()
        )
        
        if not identifier:
            raise ValueError(f"Patient with MRN {mrn} not found in facility {facility_id}")
        
        return identifier.patient

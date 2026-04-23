from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.facility import Facility
from app.models.patient import Patient
from app.models.referral import Referral
from app.enums import UserRole

class PermissionChecker:
    def __init__(self, current_user: User, db: Session):
        self.current_user = current_user
        self.db = db

    def check_super_admin_or_same_facility(self, facility_id: int) -> bool:
        """Check if user is super admin or belongs to the same facility."""
        if self.current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        if self.current_user.facility_id != facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own facility's data"
            )
        
        return True

    def check_facility_admin_or_same_facility(self, facility_id: int) -> bool:
        """Check if user is facility admin or belongs to the same facility."""
        if self.current_user.role in [UserRole.SUPER_ADMIN, UserRole.FACILITY_ADMIN]:
            return self.check_super_admin_or_same_facility(facility_id)
        
        # Clinicians can only access their own facility
        if self.current_user.role == UserRole.CLINICIAN:
            if self.current_user.facility_id != facility_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Clinicians can only access their own facility's data"
                )
            return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Insufficient permissions"
        )

    def check_patient_access(self, patient_id: int) -> bool:
        """Check if user can access patient data."""
        if self.current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Get patient and check facility access
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Check if patient belongs to user's facility
        patient_identifier = None
        for identifier in patient.identifiers:
            if identifier.facility_id == self.current_user.facility_id:
                patient_identifier = identifier
                break
        
        if not patient_identifier:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Patient not found in your facility"
            )
        
        return True

    def check_referral_access(self, referral_id: int) -> bool:
        """Check if user can access referral data."""
        if self.current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        referral = self.db.query(Referral).filter(Referral.id == referral_id).first()
        if not referral:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral not found"
            )
        
        # Check if user is from sender or receiver facility
        if (referral.from_facility_id != self.current_user.facility_id and 
            referral.to_facility_id != self.current_user.facility_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access referrals involving your facility"
            )
        
        return True

    def check_user_management(self, target_user_id: int = None, target_facility_id: int = None) -> bool:
        """Check if user can manage other users."""
        if self.current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        if self.current_user.role == UserRole.FACILITY_ADMIN:
            # Can only manage users in their facility
            if target_facility_id and target_facility_id != self.current_user.facility_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Facility admins can only manage users in their facility"
                )
            
            # Cannot manage other facility admins or super admins
            if target_user_id:
                target_user = self.db.query(User).filter(User.id == target_user_id).first()
                if target_user and target_user.role in [UserRole.SUPER_ADMIN, UserRole.FACILITY_ADMIN]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Cannot manage admin users"
                    )
            
            return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only admins can manage users"
        )

    def check_facility_access(self, facility_id: int) -> bool:
        """Check if user can access facility data."""
        if self.current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        if self.current_user.role == UserRole.FACILITY_ADMIN:
            if self.current_user.facility_id != facility_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Facility admins can only access their own facility"
                )
            return True
        
        if self.current_user.role == UserRole.CLINICIAN:
            if self.current_user.facility_id != facility_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Clinicians can only access their own facility"
                )
            return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Insufficient permissions"
        )

def get_permission_checker(current_user: User, db: Session) -> PermissionChecker:
    """Get permission checker instance."""
    return PermissionChecker(current_user, db)

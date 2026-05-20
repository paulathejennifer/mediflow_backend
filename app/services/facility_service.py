"""
Facility Service for Mediflow System

This service handles facility-related business logic including:
- Facility creation and management
- User assignment tracking
- Facility statistics
- Referral flow analysis
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status
from app.models.facility import Facility
from app.models.user import User
from app.models.referral import Referral
from app.models.patient_identifier import PatientIdentifier
from app.schemas.facility import FacilityCreate, FacilityUpdate
from app.enums import UserRole, ReferralStatus
from typing import List, Optional, Dict, Any

class FacilityService:
    """Service for facility management operations."""
    
    def __init__(self, db: Session):
        self.db = db

    def create_facility(self, facility_data: FacilityCreate, creator_id: int) -> Facility:
        """
        Create a new facility with validation and automatic code generation.

        Args:
            facility_data: Facility creation data
            creator_id: ID of user creating this facility

        Returns:
            Created facility object
        """
        # Generate or validate facility code
        facility_code = facility_data.facility_code

        if not facility_code or (isinstance(facility_code, str) and facility_code.strip() == ""):
            # Auto-generate code from facility name
            try:
                facility_code = self._generate_facility_code(facility_data.name)
            except Exception as e:
                # If generation fails, use a fallback
                facility_code = "FAC" + str(hash(facility_data.name))[:3].upper()
        else:
            # Validate uniqueness if code is provided
            existing_facility = self.db.query(Facility).filter(
                Facility.facility_code == facility_code
            ).first()
            if existing_facility:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Facility code already exists"
                )

        # Ensure facility_code is never None (database constraint)
        if not facility_code:
            try:
                facility_code = self._generate_facility_code(facility_data.name)
            except Exception as e:
                # Fallback if generation fails
                facility_code = "FAC" + str(hash(facility_data.name))[:3].upper()

        # Create facility with generated/validated code
        # Build dict manually to ensure facility_code is set
        facility = Facility(
            name=facility_data.name,
            facility_code=facility_code,
            type=facility_data.type,
            level=facility_data.level,
            county=facility_data.county,
            address=facility_data.address,
            phone=facility_data.phone,
            email=facility_data.email,
            is_active=facility_data.is_active
        )
        self.db.add(facility)
        self.db.commit()
        self.db.refresh(facility)

        return facility
    
    def _generate_facility_code(self, facility_name: str) -> str:
        """
        Generate a facility code from the facility name with duplicate handling.
        
        Args:
            facility_name: Name of the facility
            
        Returns:
            Generated facility code
        """
        # Extract initials from facility name (first letter of each word)
        words = facility_name.strip().split()
        if not words:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Facility name is required for code generation"
            )
        
        # Generate base code (uppercase initials)
        base_code = "".join([word[0].upper() for word in words if word])
        
        # Ensure code is at least 2 characters
        if len(base_code) < 2:
            base_code = (base_code + facility_name[:2]).upper()
        
        # Check if base code exists
        existing = self.db.query(Facility).filter(
            Facility.facility_code == base_code
        ).first()
        
        if not existing:
            return base_code
        
        # Handle duplicates with suffixes
        suffix = 1
        while True:
            new_code = f"{base_code}-{suffix:02d}"
            existing = self.db.query(Facility).filter(
                Facility.facility_code == new_code
            ).first()
            
            if not existing:
                return new_code
            
            suffix += 1

    def get_facility_by_id(self, facility_id: int) -> Optional[Facility]:
        """Get facility by ID."""
        return self.db.query(Facility).filter(Facility.id == facility_id).first()

    def get_facility_by_code(self, facility_code: str) -> Optional[Facility]:
        """Get facility by code."""
        return self.db.query(Facility).filter(Facility.facility_code == facility_code).first()

    def update_facility(self, facility_id: int, facility_update: FacilityUpdate, updater_id: int) -> Facility:
        """
        Update facility information.
        
        Args:
            facility_id: ID of facility to update
            facility_update: Update data
            updater_id: ID of user performing update
            
        Returns:
            Updated facility object
        """
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )
        
        update_data = facility_update.dict(exclude_unset=True)
        
        # Validate facility code uniqueness if being updated
        if "facility_code" in update_data:
            existing_facility = self.db.query(Facility).filter(
                and_(
                    Facility.facility_code == update_data["facility_code"],
                    Facility.id != facility_id
                )
            ).first()
            if existing_facility:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Facility code already exists"
                )
        
        # Apply updates
        for field, value in update_data.items():
            setattr(facility, field, value)
        
        self.db.commit()
        self.db.refresh(facility)
        
        return facility

    def deactivate_facility(self, facility_id: int, deactivator_id: int) -> Facility:
        """
        Deactivate facility.
        
        Args:
            facility_id: ID of facility to deactivate
            deactivator_id: ID of user performing deactivation
            
        Returns:
            Deactivated facility object
        """
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )
        
        if not facility.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Facility is already deactivated"
            )
        
        facility.is_active = False
        self.db.commit()
        self.db.refresh(facility)
        
        return facility

    def activate_facility(self, facility_id: int, activator_id: int) -> Facility:
        """
        Activate facility.
        
        Args:
            facility_id: ID of facility to activate
            activator_id: ID of user performing activation
            
        Returns:
            Activated facility object
        """
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )
        
        if facility.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Facility is already active"
            )
        
        facility.is_active = True
        self.db.commit()
        self.db.refresh(facility)
        
        return facility

    def list_facilities(self, skip: int = 0, limit: int = 100, county: Optional[str] = None, 
                       facility_type: Optional[str] = None, level: Optional[str] = None) -> List[Facility]:
        """
        List facilities with optional filters.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            county: Optional county filter
            facility_type: Optional facility type filter
            level: Optional facility level filter
            
        Returns:
            List of facilities
        """
        query = self.db.query(Facility).filter(Facility.is_active == True)
        
        if county:
            query = query.filter(Facility.county.ilike(f"%{county}%"))
        
        if facility_type:
            query = query.filter(Facility.type == facility_type)
        
        if level:
            query = query.filter(Facility.level == level)
        
        return query.offset(skip).limit(limit).all()

    def get_facility_users(self, facility_id: int, role: Optional[str] = None) -> List[User]:
        """
        Get users in a facility.
        
        Args:
            facility_id: Facility ID
            role: Optional role filter
            
        Returns:
            List of users in the facility
        """
        query = self.db.query(User).filter(
            and_(User.facility_id == facility_id, User.is_active == True)
        )
        
        if role:
            query = query.filter(User.role == role)
        
        return query.all()

    def get_facility_stats(self, facility_id: int) -> Dict[str, Any]:
        """
        Get comprehensive facility statistics.
        
        Args:
            facility_id: Facility ID
            
        Returns:
            Dictionary with facility statistics
        """
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facility not found"
            )
        
        # User statistics
        total_users = self.db.query(User).filter(User.facility_id == facility_id).count()
        active_users = self.db.query(User).filter(
            and_(User.facility_id == facility_id, User.is_active == True)
        ).count()
        
        # User role breakdown
        role_stats = {}
        for role in UserRole:
            role_count = self.db.query(User).filter(
                and_(User.facility_id == facility_id, User.role == role.value, User.is_active == True)
            ).count()
            role_stats[role.value] = role_count
        
        # Patient statistics
        patient_count = self.db.query(PatientIdentifier).filter(
            PatientIdentifier.facility_id == facility_id
        ).count()
        
        # Referral statistics
        sent_referrals = self.db.query(Referral).filter(
            Referral.from_facility_id == facility_id
        ).count()
        
        received_referrals = self.db.query(Referral).filter(
            Referral.to_facility_id == facility_id
        ).count()
        
        # Referral status breakdown
        referral_status_stats = {}
        for status in ReferralStatus:
            status_count = self.db.query(Referral).filter(
                and_(
                    or_(
                        Referral.from_facility_id == facility_id,
                        Referral.to_facility_id == facility_id
                    ),
                    Referral.status == status.value
                )
            ).count()
            referral_status_stats[status.value] = status_count
        
        return {
            "facility_info": {
                "id": facility.id,
                "name": facility.name,
                "code": facility.facility_code,
                "type": facility.type,
                "level": facility.level,
                "county": facility.county
            },
            "user_stats": {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "role_breakdown": role_stats
            },
            "patient_stats": {
                "total_patients": patient_count
            },
            "referral_stats": {
                "sent_referrals": sent_referrals,
                "received_referrals": received_referrals,
                "total_referrals": sent_referrals + received_referrals,
                "status_breakdown": referral_status_stats
            }
        }

    def get_referral_partners(self, facility_id: int) -> List[Dict[str, Any]]:
        """
        Get facilities that this facility frequently refers to/receives from.
        
        Args:
            facility_id: Facility ID
            
        Returns:
            List of partner facilities with referral counts
        """
        # Get facilities this facility sends to
        sent_to = (
            self.db.query(
                Referral.to_facility_id,
                Facility.name,
                Facility.facility_code,
                func.count(Referral.id).label('referral_count')
            )
            .join(Facility, Referral.to_facility_id == Facility.id)
            .filter(Referral.from_facility_id == facility_id)
            .group_by(Referral.to_facility_id, Facility.name, Facility.facility_code)
            .all()
        )
        
        # Get facilities this facility receives from
        received_from = (
            self.db.query(
                Referral.from_facility_id,
                Facility.name,
                Facility.facility_code,
                func.count(Referral.id).label('referral_count')
            )
            .join(Facility, Referral.from_facility_id == Facility.id)
            .filter(Referral.to_facility_id == facility_id)
            .group_by(Referral.from_facility_id, Facility.name, Facility.facility_code)
            .all()
        )
        
        partners = []
        
        # Process sent referrals
        for partner in sent_to:
            partners.append({
                "facility_id": partner.to_facility_id,
                "name": partner.name,
                "facility_code": partner.facility_code,
                "relationship": "sends_to",
                "referral_count": partner.referral_count
            })
        
        # Process received referrals
        for partner in received_from:
            partners.append({
                "facility_id": partner.from_facility_id,
                "name": partner.name,
                "facility_code": partner.facility_code,
                "relationship": "receives_from",
                "referral_count": partner.referral_count
            })
        
        return partners

    def search_facilities(self, query: str, limit: int = 20) -> List[Facility]:
        """
        Search facilities by name, code, or county.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching facilities
        """
        search_term = f"%{query}%"
        return (
            self.db.query(Facility)
            .filter(
                and_(
                    Facility.is_active == True,
                    or_(
                        Facility.name.ilike(search_term),
                        Facility.facility_code.ilike(search_term),
                        Facility.county.ilike(search_term)
                    )
                )
            )
            .limit(limit)
            .all()
        )

def get_facility_service(db: Session) -> FacilityService:
    """Get facility service instance."""
    return FacilityService(db)

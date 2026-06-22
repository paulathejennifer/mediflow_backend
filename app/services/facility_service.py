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
from fastapi import HTTPException
from fastapi import status as http_status
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

    def create_facility(
        self, facility_data: FacilityCreate, creator_id: int
    ) -> Facility:
        """Create a new facility with validation and automatic code generation."""
        facility_code = facility_data.facility_code

        if not facility_code or (isinstance(facility_code, str) and facility_code.strip() == ""):
            facility_code = self._generate_facility_code(facility_data.name)

        # Validate uniqueness
        existing = self.db.query(Facility).filter(Facility.facility_code == facility_code).first()
        if existing:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Facility code already exists"
            )

        facility = Facility(
            name=facility_data.name,
            facility_code=facility_code,
            type=facility_data.type,
            level=facility_data.level,
            county=facility_data.county,
            address=facility_data.address,
            phone=facility_data.phone,
            email=facility_data.email,
            is_active=True, 
            performance_score=0.0,  # Start with 0
        )

        self.db.add(facility)
        self.db.commit()
        self.db.refresh(facility)

        return facility

    def _generate_facility_code(self, facility_name: str) -> str:
        """Generate a facility code from the facility name with duplicate handling."""
        words = facility_name.strip().split()
        if not words:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Facility name is required for code generation"
            )

        base_code = "".join([word[0].upper() for word in words if word])
        if len(base_code) < 2:
            base_code = (base_code + facility_name[:2]).upper()

        # Check for duplicates
        existing = self.db.query(Facility).filter(Facility.facility_code == base_code).first()
        if not existing:
            return base_code

        suffix = 1
        while True:
            new_code = f"{base_code}-{suffix:02d}"
            if not self.db.query(Facility).filter(Facility.facility_code == new_code).first():
                return new_code
            suffix += 1

    def get_facility_by_id(self, facility_id: int) -> Optional[Facility]:
        return self.db.query(Facility).filter(Facility.id == facility_id).first()

    def get_facility_by_code(self, facility_code: str) -> Optional[Facility]:
        return self.db.query(Facility).filter(Facility.facility_code == facility_code).first()

    def list_facilities(
        self,
        skip: int = 0,
        limit: int = 100,
        county: Optional[str] = None,
        facility_type: Optional[str] = None,
        level: Optional[str] = None,
        calculate_performance: bool = True,   # New parameter
    ) -> List[Facility]:
        """List facilities with optional filters and optional real-time performance calculation."""
        query = self.db.query(Facility).filter(Facility.is_active == True)

        if county:
            query = query.filter(Facility.county.ilike(f"%{county}%"))
        if facility_type:
            query = query.filter(Facility.type == facility_type)
        if level:
            query = query.filter(Facility.level == level)

        facilities = query.offset(skip).limit(limit).all()

        # Calculate real performance if requested
        if calculate_performance:
            for facility in facilities:
                try:
                    stats = self.get_facility_stats(facility.id)
                    facility.performance_score = stats.get("facility_info", {}).get("performance", 0.0)
                except Exception:
                    # Keep existing score if calculation fails
                    pass

        return facilities

    def update_facility(
        self, facility_id: int, facility_update: FacilityUpdate, updater_id: int
    ) -> Facility:
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Facility not found")

        update_data = facility_update.dict(exclude_unset=True)

        if "facility_code" in update_data:
            existing = self.db.query(Facility).filter(
                and_(
                    Facility.facility_code == update_data["facility_code"],
                    Facility.id != facility_id
                )
            ).first()
            if existing:
                raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Facility code already exists")

        for field, value in update_data.items():
            setattr(facility, field, value)

        self.db.commit()
        self.db.refresh(facility)
        return facility

    def deactivate_facility(self, facility_id: int, deactivator_id: int) -> Facility:
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Facility not found")
        if not facility.is_active:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Facility is already deactivated")

        facility.is_active = False
        self.db.commit()
        self.db.refresh(facility)
        return facility

    def activate_facility(self, facility_id: int, activator_id: int) -> Facility:
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Facility not found")
        if facility.is_active:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Facility is already active")

        facility.is_active = True
        self.db.commit()
        self.db.refresh(facility)
        return facility

    def get_facility_users(self, facility_id: int, role: Optional[str] = None) -> List[User]:
        query = self.db.query(User).filter(
            and_(User.facility_id == facility_id, User.is_active == True)
        )
        if role:
            query = query.filter(User.role == role)
        return query.all()

    def get_facility_stats(self, facility_id: int) -> Dict[str, Any]:
        """Get comprehensive facility statistics with real performance score."""
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Facility not found")

        # Referral statistics
        sent_referrals = self.db.query(Referral).filter(Referral.from_facility_id == facility_id).count()
        received_referrals = self.db.query(Referral).filter(Referral.to_facility_id == facility_id).count()

        # Completed referrals
        completed = self.db.query(Referral).filter(
            and_(
                or_(
                    Referral.from_facility_id == facility_id,
                    Referral.to_facility_id == facility_id
                ),
                Referral.status == ReferralStatus.COMPLETED.value
            )
        ).count()

        total_referrals = sent_referrals + received_referrals
        performance = round((completed / max(total_referrals, 1)) * 100, 1)

        # Update the facility record
        facility.performance_score = performance
        self.db.commit()

        return {
            "facility_info": {
                "id": facility.id,
                "name": facility.name,
                "code": facility.facility_code,
                "type": facility.type,
                "level": facility.level,
                "county": facility.county,
                "performance": performance
            },
            "referral_stats": {
                "sent_referrals": sent_referrals,
                "received_referrals": received_referrals,
                "total_referrals": total_referrals,
                "completed_referrals": completed,
                "completion_rate": performance
            }
        }

    # ... (keep other methods like get_referral_partners, search_facilities unchanged)

    def get_referral_partners(self, facility_id: int) -> List[Dict[str, Any]]:
        """Get referral partner facilities."""
        # (Your existing implementation - unchanged)
        sent_to = (
            self.db.query(
                Referral.to_facility_id,
                Facility.name,
                Facility.facility_code,
                func.count(Referral.id).label("referral_count"),
            )
            .join(Facility, Referral.to_facility_id == Facility.id)
            .filter(Referral.from_facility_id == facility_id)
            .group_by(Referral.to_facility_id, Facility.name, Facility.facility_code)
            .all()
        )

        received_from = (
            self.db.query(
                Referral.from_facility_id,
                Facility.name,
                Facility.facility_code,
                func.count(Referral.id).label("referral_count"),
            )
            .join(Facility, Referral.from_facility_id == Facility.id)
            .filter(Referral.to_facility_id == facility_id)
            .group_by(Referral.from_facility_id, Facility.name, Facility.facility_code)
            .all()
        )

        partners = []
        for p in sent_to:
            partners.append({
                "facility_id": p.to_facility_id,
                "name": p.name,
                "facility_code": p.facility_code,
                "relationship": "sends_to",
                "referral_count": p.referral_count,
            })
        for p in received_from:
            partners.append({
                "facility_id": p.from_facility_id,
                "name": p.name,
                "facility_code": p.facility_code,
                "relationship": "receives_from",
                "referral_count": p.referral_count,
            })

        return partners

    def search_facilities(self, query: str, limit: int = 20) -> List[Facility]:
        search_term = f"%{query}%"
        return (
            self.db.query(Facility)
            .filter(
                and_(
                    Facility.is_active == True,
                    or_(
                        Facility.name.ilike(search_term),
                        Facility.facility_code.ilike(search_term),
                        Facility.county.ilike(search_term),
                    ),
                )
            )
            .limit(limit)
            .all()
        )


def get_facility_service(db: Session) -> FacilityService:
    """Get facility service instance."""
    return FacilityService(db)
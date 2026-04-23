from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.enums import FacilityType, FacilityLevel

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    facility_code = Column(String, unique=True, nullable=False, index=True)
    type = Column(String, nullable=False)
    level = Column(String, nullable=False)
    county = Column(String, nullable=False)
    address = Column(Text, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_active = Column(String, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="facility")
    patients = relationship("PatientIdentifier", back_populates="facility")
    from_referrals = relationship("Referral", foreign_keys="Referral.from_facility_id", back_populates="from_facility")
    to_referrals = relationship("Referral", foreign_keys="Referral.to_facility_id", back_populates="to_facility")
    counter = relationship("FacilityCounter", back_populates="facility", uselist=False)

    def __repr__(self):
        return f"<Facility(id={self.id}, name={self.name}, code={self.facility_code})>"

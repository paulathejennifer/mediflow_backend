from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class FacilityCounter(Base):
    __tablename__ = "facility_counters"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), unique=True, nullable=False)
    last_patient_number = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    facility = relationship("Facility", back_populates="counter")

    def __repr__(self):
        return f"<FacilityCounter(facility_id={self.facility_id}, last_number={self.last_patient_number})>"

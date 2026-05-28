from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class PatientIdentifier(Base):
    __tablename__ = "patient_identifiers"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", name="fk_identifier_patient"), nullable=False)
    identifier_type = Column(String(50), nullable=False)
    identifier_value = Column(String(100), nullable=False)
    facility_id = Column(Integer, ForeignKey("facilities.id", name="fk_identifier_facility"), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=True)
    mrn = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="identifiers")
    facility = relationship("Facility", back_populates="patients")

    # Unique constraint: MRN must be unique per facility
    __table_args__ = (
        UniqueConstraint('facility_id', 'mrn', name='unique_facility_mrn'),
    )

    def __repr__(self):
        return f"<PatientIdentifier(mrn={self.mrn}, facility_id={self.facility_id})>"

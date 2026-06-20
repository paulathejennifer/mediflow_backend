from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime
from app.core.database import Base

class DuplicatePatientPair(Base):
    """
    Hybrid Production Model tracking evaluated structural variations.
    Combines deep administrative auditing with flexible text columns.
    """
    __tablename__ = "duplicate_patient_pairs"

    id = Column(Integer, primary_key=True, index=True)
    new_patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    existing_patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    
    # ML Scoring Metrics
    tfidf_similarity = Column(Float, nullable=False) 
    fuzzy_ratio = Column(Float, nullable=False)       
    combined_score = Column(Float, nullable=False)    
    
    # Workflow Status (Uses String for migration safety)
    status = Column(String, default="flagged", nullable=False) # flagged, merged, dismissed
    
    # Full Operational Audit Trail
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Cross-table Relationships
    new_patient = relationship("Patient", foreign_keys=[new_patient_id])
    existing_patient = relationship("Patient", foreign_keys=[existing_patient_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
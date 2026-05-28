from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.enums import ReferralStatus, Priority

class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", name="fk_referral_patient"), nullable=False)
    from_facility_id = Column(Integer, ForeignKey("facilities.id", name="fk_referral_from_facility"), nullable=False)
    to_facility_id = Column(Integer, ForeignKey("facilities.id", name="fk_referral_to_facility"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", name="fk_referral_creator"), nullable=False)
    priority = Column(String, nullable=False, default=Priority.MEDIUM)
    status = Column(String, nullable=False, default=ReferralStatus.DRAFT)
    reason_for_referral = Column(Text, nullable=True)
    clinical_notes = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    ai_status = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="referrals")
    from_facility = relationship("Facility", foreign_keys=[from_facility_id], back_populates="from_referrals")
    to_facility = relationship("Facility", foreign_keys=[to_facility_id], back_populates="to_referrals")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_referrals")
    documents = relationship("ReferralDocument", back_populates="referral")
    voice_notes = relationship("VoiceNote", back_populates="referral")

    def __repr__(self):
        return f"<Referral(id={self.id}, status={self.status}, priority={self.priority})>"

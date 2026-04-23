from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.enums import VoiceStatus

class VoiceNote(Base):
    __tablename__ = "voice_notes"

    id = Column(Integer, primary_key=True, index=True)
    referral_id = Column(Integer, ForeignKey("referrals.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    audio_path = Column(String, nullable=False)
    audio_file_name = Column(String, nullable=False)
    audio_file_size = Column(Integer, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    processed_transcript = Column(Text, nullable=True)
    status = Column(String, nullable=False, default=VoiceStatus.UPLOADED)
    ai_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    referral = relationship("Referral", back_populates="voice_notes")
    uploader = relationship("User")

    def __repr__(self):
        return f"<VoiceNote(id={self.id}, status={self.status}, duration={self.duration_seconds})>"

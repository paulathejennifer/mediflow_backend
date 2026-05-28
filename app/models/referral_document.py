from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.enums import DocumentType

class ReferralDocument(Base):
    __tablename__ = "referral_documents"

    id = Column(Integer, primary_key=True, index=True)
    referral_id = Column(Integer, ForeignKey("referrals.id", name="fk_document_referral"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", name="fk_document_uploader"), nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    extracted_text = Column(Text, nullable=True)
    ai_processed = Column(String, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    referral = relationship("Referral", back_populates="documents")
    uploader = relationship("User")

    def __repr__(self):
        return f"<ReferralDocument(id={self.id}, file_name={self.file_name}, type={self.file_type})>"

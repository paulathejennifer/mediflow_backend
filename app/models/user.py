from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.CLINICIAN)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=True)
    is_active = Column(String, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    facility = relationship("Facility", back_populates="users")
    created_referrals = relationship("Referral", foreign_keys="Referral.created_by", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user")
    # notifications = relationship("Notification", back_populates="user")  # TODO: Uncomment when notification system is implemented
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    email_verification_tokens = relationship("EmailVerificationToken", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

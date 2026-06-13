from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class ReferralBase(BaseModel):
    patient_id: int
    to_facility_id: int
    priority: Optional[str] = "medium"
    reason_for_referral: Optional[str] = None
    clinical_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ReferralCreate(ReferralBase):
    pass


class ReferralUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    reason_for_referral: Optional[str] = None
    clinical_notes: Optional[str] = None
    notes: Optional[str] = None


class ReferralResponse(ReferralBase):
    id: int
    from_facility_id: int
    created_by: int
    status: str
    ai_summary: Optional[str] = None
    ai_status: Optional[str] = None
    notes: Optional[str] = None
    reason_for_referral: Optional[str] = None
    
    # Milestone Timestamps
    submitted_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    accepted_by: Optional[int] = None
    completed_by: Optional[int] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PatientDetail(BaseModel):
    id: int
    first_name: str
    last_name: str
    model_config = ConfigDict(from_attributes=True)


class FacilityDetail(BaseModel):
    id: int
    name: str
    facility_code: str
    model_config = ConfigDict(from_attributes=True)


class UserDetail(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(BaseModel):
    id: int
    file_name: str
    file_type: str
    model_config = ConfigDict(from_attributes=True)


class VoiceNoteDetail(BaseModel):
    id: int
    audio_file_name: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class ReferralSummary(BaseModel):
    id: int
    patient_name: str
    from_facility_name: str
    from_facility_id: int
    to_facility_name: str
    to_facility_id: int
    status: str
    priority: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReferralWithDetails(ReferralResponse):
    patient: Optional[PatientDetail] = None
    from_facility: Optional[FacilityDetail] = None
    to_facility: Optional[FacilityDetail] = None
    creator: Optional[UserDetail] = None
    accepted_by_user: Optional[UserDetail] = None
    rejected_by_user: Optional[UserDetail] = None
    completed_by_user: Optional[UserDetail] = None
    documents: List[DocumentDetail] = []
    voice_notes: List[VoiceNoteDetail] = []

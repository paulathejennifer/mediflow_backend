from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ReferralBase(BaseModel):
    patient_id: int
    to_facility_id: int
    priority: Optional[str] = "medium"
    reason_for_referral: Optional[str] = None
    clinical_notes: Optional[str] = None


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
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReferralSummary(BaseModel):
    id: int
    patient_name: str
    from_facility_name: str
    to_facility_name: str
    status: str
    priority: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReferralWithDetails(ReferralResponse):
    patient: Optional[dict] = None
    from_facility: Optional[dict] = None
    to_facility: Optional[dict] = None
    creator: Optional[dict] = None
    documents: List[dict] = []
    voice_notes: List[dict] = []

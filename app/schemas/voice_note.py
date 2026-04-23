from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VoiceNoteBase(BaseModel):
    audio_file_name: str
    audio_file_size: int
    duration_seconds: Optional[int] = None

class VoiceNoteCreate(VoiceNoteBase):
    referral_id: int
    audio_path: str

class VoiceNoteUpdate(BaseModel):
    transcript: Optional[str] = None
    processed_transcript: Optional[str] = None
    status: Optional[str] = None
    ai_summary: Optional[str] = None

class VoiceNoteResponse(VoiceNoteBase):
    id: int
    referral_id: int
    uploaded_by: int
    audio_path: str
    transcript: Optional[str] = None
    processed_transcript: Optional[str] = None
    status: str
    ai_summary: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class VoiceNoteSummary(BaseModel):
    id: int
    audio_file_name: str
    duration_seconds: Optional[int] = None
    status: str
    created_at: datetime
    uploader_name: Optional[str] = None
    
    class Config:
        from_attributes = True

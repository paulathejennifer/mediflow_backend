from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentBase(BaseModel):
    file_type: str
    file_name: str
    file_size: int
    mime_type: str

class DocumentCreate(DocumentBase):
    referral_id: int
    file_path: str

class DocumentResponse(DocumentBase):
    id: int
    referral_id: int
    uploaded_by: int
    file_path: str
    extracted_text: Optional[str] = None
    ai_processed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DocumentSummary(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_size: int
    created_at: datetime
    uploader_name: Optional[str] = None
    
    class Config:
        from_attributes = True

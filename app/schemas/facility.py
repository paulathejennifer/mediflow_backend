from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FacilityBase(BaseModel):
    name: str
    facility_code: str
    type: str
    level: str
    county: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = True

class FacilityCreate(FacilityBase):
    pass

class FacilityUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    level: Optional[str] = None
    county: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

class FacilityResponse(FacilityBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class FacilitySummary(BaseModel):
    id: int
    name: str
    facility_code: str
    type: str
    level: str
    county: str
    
    class Config:
        from_attributes = True

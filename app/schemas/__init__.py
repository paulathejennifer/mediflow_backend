from app.schemas.auth import (
    UserLogin,
    Token,
    TokenData,
    UserCreate,
    UserResponse,
    PasswordChange,
)
from app.schemas.user import UserBase, UserCreate, UserUpdate, UserResponse, UserInDB
from app.schemas.facility import (
    FacilityBase,
    FacilityCreate,
    FacilityUpdate,
    FacilityResponse,
    FacilitySummary,
)
from app.schemas.patient import (
    PatientBase,
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientIdentifier,
    PatientWithIdentifiers,
)
from app.schemas.referral import (
    ReferralBase,
    ReferralCreate,
    ReferralUpdate,
    ReferralResponse,
    ReferralSummary,
    ReferralWithDetails,
)
from app.schemas.document import (
    DocumentBase,
    DocumentCreate,
    DocumentResponse,
    DocumentSummary,
)
from app.schemas.voice_note import (
    VoiceNoteBase,
    VoiceNoteCreate,
    VoiceNoteUpdate,
    VoiceNoteResponse,
    VoiceNoteSummary,
)

__all__ = [
    # Auth
    "UserLogin",
    "Token",
    "TokenData",
    "UserCreate",
    "UserResponse",
    "PasswordChange",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Facility
    "FacilityBase",
    "FacilityCreate",
    "FacilityUpdate",
    "FacilityResponse",
    "FacilitySummary",
    # Patient
    "PatientBase",
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    "PatientIdentifier",
    "PatientWithIdentifiers",
    # Referral
    "ReferralBase",
    "ReferralCreate",
    "ReferralUpdate",
    "ReferralResponse",
    "ReferralSummary",
    "ReferralWithDetails",
    # Document
    "DocumentBase",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentSummary",
    # Voice Note
    "VoiceNoteBase",
    "VoiceNoteCreate",
    "VoiceNoteUpdate",
    "VoiceNoteResponse",
    "VoiceNoteSummary",
]

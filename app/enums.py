from enum import Enum

# Core system
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    FACILITY_ADMIN = "facility_admin"
    CLINICIAN = "clinician"
    PATIENT = "patient"

# Patient
class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

# Facility
class FacilityType(str, Enum):
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    HEALTH_CENTER = "health_center"
    DISPENSARY = "dispensary"
    REFERRAL_CENTER = "referral_center"

class FacilityLevel(str, Enum):
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    LEVEL_4 = "level_4"
    LEVEL_5 = "level_5"
    LEVEL_6 = "level_6"

# Referral
class ReferralStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    COMPLETED = "completed"
    REJECTED = "rejected"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"

# Documents
class DocumentType(str, Enum):
    LAB_REPORT = "lab_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    PRESCRIPTION = "prescription"
    IMAGING = "imaging"
    REFERRAL_NOTE = "referral_note"
    OTHER = "other"

# Voice
class VoiceStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    TRANSCRIBED = "transcribed"
    FAILED = "failed"

# AI Processing
class AIStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Audit Actions
class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    VIEW = "view"

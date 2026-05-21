# MediFlow Backend API Documentation

## Overview

MediFlow is an inter-facility patient referral system built with FastAPI, designed to streamline healthcare referrals between medical facilities in Kenya. This document provides comprehensive API documentation for frontend integration.

---

## Base URL

```
http://localhost:8000/api/v1
```

---

## Authentication

### Authentication Method
- **Bearer Token** (JWT)
- **Header**: `Authorization: Bearer <token>`

### Endpoints

#### POST `/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+254712345678",
  "password": "securePassword123",
  "role": "clinician",
  "facility_id": 1
}
```

**Response:**
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+254712345678",
  "role": "clinician",
  "facility_id": 1,
  "is_active": true,
  "created_at": "2024-05-15T00:00:00Z"
}
```

#### POST `/auth/login`
Login user and receive access and refresh tokens.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securePassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Token Details:**
- **Access Token**: Short-lived (30 minutes), used for API authentication
- **Refresh Token**: Long-lived (7 days), used to obtain new access tokens
- **Token Type**: Always "bearer"

#### GET `/auth/me`
Get current authenticated user information.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+254712345678",
  "role": "clinician",
  "facility_id": 1,
  "is_active": true,
  "created_at": "2024-05-15T00:00:00Z"
}
```

#### POST `/auth/change-password`
Change user password.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "current_password": "securePassword123",
  "new_password": "newSecurePassword456"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

#### POST `/auth/logout`
Logout user (client-side token removal).

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Logout successful"
}
```

#### POST `/auth/forgot-password`
Request password reset email.

**Request Body:**
```json
{
  "email": "john@example.com"
}
```

**Response:**
```json
{
  "message": "Password reset email sent."
}
```

#### POST `/auth/reset-password`
Reset password using token from email.

**Request Body:**
```json
{
  "token": "reset_token_from_email",
  "new_password": "newSecurePassword456"
}
```

**Response:**
```json
{
  "message": "Password reset successfully"
}
```

#### POST `/auth/verify-email`
Verify email address using token.

**Request Body:**
```json
{
  "token": "verification_token_from_email"
}
```

**Response:**
```json
{
  "message": "Email verified successfully"
}
```

#### POST `/auth/resend-verification`
Resend email verification token.

**Request Body:**
```json
{
  "email": "john@example.com"
}
```

**Response:**
```json
{
  "message": "Verification email sent."
}
```

#### POST `/auth/verify-code`
Verify a verification code (for phone/SMS verification).

**Request Body:**
```json
{
  "code": "123456"
}
```

**Response:**
```json
{
  "message": "Code verified successfully"
}
```

#### POST `/auth/refresh-token`
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "new_access_token_string",
  "token_type": "bearer"
}
```

**Refresh Token Flow:**
```typescript
// 1. Initial login - get both tokens
const loginResponse = await POST /auth/login
const { access_token, refresh_token } = loginResponse

// 2. Store both tokens securely
localStorage.setItem('access_token', access_token)
localStorage.setItem('refresh_token', refresh_token)

// 3. Use access_token for API calls
const apiResponse = await GET /api/v1/patients
Headers: Authorization: Bearer ${access_token}

// 4. When access token expires (401 error)
const refreshResponse = await POST /auth/refresh-token
{ refresh_token: stored_refresh_token }

// 5. Update access token with new one
localStorage.setItem('access_token', refreshResponse.access_token)

// 6. Retry original API call with new access token
```

**Important Notes:**
- Refresh tokens are stored in the database and can be revoked
- Refresh tokens expire after 7 days by default
- If refresh token is invalid/expired, user must login again
- Always store tokens securely (httpOnly cookies recommended for production)

---

## User Roles

### Available Roles
- `super_admin` - System-wide administrative access
- `facility_admin` - Facility-specific administrative access
- `clinician` - Clinical staff with patient/referral access
- `patient` - Patient access (limited functionality)

---

## Patients

### Model Fields
```typescript
{
  id: number,
  first_name: string,
  last_name: string,
  date_of_birth: string, // ISO date format
  gender: string, // "male", "female", "other"
  phone: string,
  email: string,
  address: string,
  emergency_contact_name: string,
  emergency_contact_phone: string,
  medical_history: string,
  allergies: string,
  medications: string,
  chronic_conditions: string,
  created_at: string, // ISO datetime
  updated_at: string // ISO datetime
}
```

### Endpoints

#### POST `/patients/`
Create a new patient with automatic MRN generation.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "date_of_birth": "1985-03-15",
  "gender": "female",
  "phone": "+254723456789",
  "email": "jane.smith@email.com",
  "address": "123 Main Street, Nairobi",
  "emergency_contact_name": "John Smith",
  "emergency_contact_phone": "+254723456788",
  "medical_history": "2018: Diagnosed with hypertension\n2020: Treated for pneumonia",
  "allergies": "Penicillin, Shellfish",
  "medications": "Lisinopril 10mg daily, Metformin 500mg twice daily",
  "chronic_conditions": "Hypertension, Type 2 Diabetes"
}
```

**Response:**
```json
{
  "id": 1,
  "first_name": "Jane",
  "last_name": "Smith",
  "date_of_birth": "1985-03-15",
  "gender": "female",
  "phone": "+254723456789",
  "email": "jane.smith@email.com",
  "address": "123 Main Street, Nairobi",
  "emergency_contact_name": "John Smith",
  "emergency_contact_phone": "+254723456788",
  "medical_history": "2018: Diagnosed with hypertension\n2020: Treated for pneumonia",
  "allergies": "Penicillin, Shellfish",
  "medications": "Lisinopril 10mg daily, Metformin 500mg twice daily",
  "chronic_conditions": "Hypertension, Type 2 Diabetes",
  "created_at": "2024-05-15T00:00:00Z",
  "updated_at": "2024-05-15T00:00:00Z",
  "identifiers": [
    {
      "id": 1,
      "mrn": "KNH-2024-0001-7",
      "facility_id": 1,
      "facility_name": "Kenyatta National Hospital",
      "facility_code": "KNH",
      "created_at": "2024-05-15T00:00:00Z"
    }
  ]
}
```

#### GET `/patients/`
List patients accessible to current user.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (integer, default: 0) - Number of records to skip
- `limit` (integer, default: 100, max: 1000) - Maximum records to return
- `search` (string, optional) - Search by name or phone

**Response:**
```json
[
  {
    "id": 1,
    "first_name": "Jane",
    "last_name": "Smith",
    "date_of_birth": "1985-03-15",
    "gender": "female",
    "phone": "+254723456789",
    "email": "jane.smith@email.com",
    "address": "123 Main Street, Nairobi",
    "emergency_contact_name": "John Smith",
    "emergency_contact_phone": "+254723456788",
    "medical_history": "2018: Diagnosed with hypertension\n2020: Treated for pneumonia",
    "allergies": "Penicillin, Shellfish",
    "medications": "Lisinopril 10mg daily, Metformin 500mg twice daily",
    "chronic_conditions": "Hypertension, Type 2 Diabetes",
    "created_at": "2024-05-15T00:00:00Z",
    "updated_at": "2024-05-15T00:00:00Z",
    "identifiers": [
      {
        "id": 1,
        "mrn": "KNH-2024-0001-7",
        "facility_id": 1,
        "facility_name": "Kenyatta National Hospital",
        "facility_code": "KNH",
        "created_at": "2024-05-15T00:00:00Z"
      }
    ]
  }
]
```

#### GET `/patients/{patient_id}`
Get patient by ID.

**Headers:** `Authorization: Bearer <token>`

**Response:** Same as POST `/patients/` response

#### GET `/patients/mrn/{mrn}`
Get patient by MRN (Medical Record Number).

**Headers:** `Authorization: Bearer <token>`

**URL Parameter:** `mrn` - Medical Record Number (e.g., "KNH-2024-0001-7")

**Response:** Same as POST `/patients/` response

#### PUT `/patients/{patient_id}`
Update patient details.

**Headers:** `Authorization: Bearer <token>`

**Request Body:** (All fields optional)
```json
{
  "first_name": "Jane",
  "last_name": "Johnson",
  "phone": "+254723456789",
  "allergies": "Penicillin, Shellfish, Latex"
}
```

**Response:** Same as POST `/patients/` response

---

## Facilities

### Model Fields
```typescript
{
  id: number,
  name: string,
  facility_code: string, // Unique 3-4 character code
  type: string, // "hospital", "clinic", "health_center", "dispensary", "referral_center"
  level: string, // "level_1" to "level_6"
  county: string,
  address: string,
  phone: string,
  email: string,
  is_active: boolean,
  created_at: string,
  updated_at: string
}
```

### Endpoints

#### POST `/facilities/`
Create a new facility (Super Admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Kenyatta National Hospital",
  "facility_code": "KNH",
  "type": "hospital",
  "level": "level_6",
  "county": "Nairobi",
  "address": "Hospital Road, Nairobi",
  "phone": "+254720000000",
  "email": "info@knh.go.ke",
  "is_active": true
}
```

**Facility Code Generation:**
- **If `facility_code` is provided**: Backend validates uniqueness
- **If `facility_code` is blank/omitted**: Backend auto-generates from facility name
- **Generation Logic**: Extracts initials from name (e.g., "Kenyatta National Hospital" → "KNH")
- **Duplicate Handling**: Adds suffixes (KNH, KNH-01, KNH-02, etc.)

**Examples:**
- "Kenyatta National Hospital" → "KNH"
- "Moi Teaching and Referral Hospital" → "MTRH"
- If KNH exists → "KNH-01", "KNH-02", etc.

**Response:**
```json
{
  "id": 1,
  "name": "Kenyatta National Hospital",
  "facility_code": "KNH",
  "type": "hospital",
  "level": "level_6",
  "county": "Nairobi",
  "address": "Hospital Road, Nairobi",
  "phone": "+254720000000",
  "email": "info@knh.go.ke",
  "is_active": true,
  "created_at": "2024-05-15T00:00:00Z",
  "updated_at": "2024-05-15T00:00:00Z"
}
```

#### GET `/facilities/`
List facilities.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (integer, default: 0)
- `limit` (integer, default: 100)
- `county` (string, optional)
- `facility_type` (string, optional)
- `level` (string, optional)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Kenyatta National Hospital",
    "facility_code": "KNH",
    "type": "hospital",
    "level": "level_6",
    "county": "Nairobi",
    "address": "Hospital Road, Nairobi",
    "phone": "+254720000000",
    "email": "info@knh.go.ke",
    "is_active": true,
    "created_at": "2024-05-15T00:00:00Z",
    "updated_at": "2024-05-15T00:00:00Z"
  }
]
```

#### GET `/facilities/{facility_id}`
Get facility by ID.

**Headers:** `Authorization: Bearer <token>`

**Response:** Same as POST `/facilities/` response

#### PUT `/facilities/{facility_id}`
Update facility details.

**Headers:** `Authorization: Bearer <token>`

**Request Body:** (All fields optional)
```json
{
  "name": "Kenyatta National Hospital",
  "phone": "+254720000001"
}
```

**Response:** Same as POST `/facilities/` response

---

## Users

### Model Fields
```typescript
{
  id: number,
  first_name: string,
  last_name: string,
  email: string,
  phone: string,
  role: string, // "super_admin", "facility_admin", "clinician", "patient"
  facility_id: number,
  is_active: boolean,
  created_at: string,
  updated_at: string
}
```

### Endpoints

#### POST `/users/`
Create a new user.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+254712345678",
  "password": "securePassword123",
  "role": "clinician",
  "facility_id": 1,
  "is_active": true
}
```

**Response:**
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+254712345678",
  "role": "clinician",
  "facility_id": 1,
  "is_active": true,
  "created_at": "2024-05-15T00:00:00Z",
  "updated_at": "2024-05-15T00:00:00Z"
}
```

#### GET `/users/`
List users.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (integer, default: 0)
- `limit` (integer, default: 100)
- `role` (string, optional)
- `facility_id` (integer, optional)

**Response:**
```json
[
  {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+254712345678",
    "role": "clinician",
    "facility_id": 1,
    "is_active": true,
    "created_at": "2024-05-15T00:00:00Z",
    "updated_at": "2024-05-15T00:00:00Z"
  }
]
```

#### GET `/users/{user_id}`
Get user by ID.

**Headers:** `Authorization: Bearer <token>`

**Response:** Same as POST `/users/` response

#### PUT `/users/{user_id}`
Update user details.

**Headers:** `Authorization: Bearer <token>`

**Request Body:** (All fields optional)
```json
{
  "first_name": "John",
  "phone": "+254712345679",
  "is_active": false
}
```

**Response:** Same as POST `/users/` response

---

## Referrals

### Model Fields
```typescript
{
  id: number,
  patient_id: number,
  from_facility_id: number,
  to_facility_id: number,
  created_by: number,
  priority: string, // "low", "medium", "high", "emergency"
  status: string, // "draft", "submitted", "accepted", "in_transit", "received", "completed", "rejected"
  reason_for_referral: string,
  clinical_notes: string,
  ai_summary: string,
  ai_status: string,
  notes: string,
  created_at: string,
  updated_at: string
}
```

### Endpoints

#### POST `/referrals/`
Create a new referral.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "patient_id": 1,
  "to_facility_id": 2,
  "priority": "high",
  "reason_for_referral": "Suspected cardiac arrhythmia requiring specialist evaluation",
  "clinical_notes": "Patient presents with palpitations, shortness of breath, and chest discomfort. ECG confirms intermittent atrial fibrillation."
}
```

**Response:**
```json
{
  "id": 1,
  "patient_id": 1,
  "from_facility_id": 1,
  "to_facility_id": 2,
  "created_by": 1,
  "priority": "high",
  "status": "draft",
  "reason_for_referral": "Suspected cardiac arrhythmia requiring specialist evaluation",
  "clinical_notes": "Patient presents with palpitations, shortness of breath, and chest discomfort. ECG confirms intermittent atrial fibrillation.",
  "ai_summary": null,
  "ai_status": null,
  "notes": null,
  "created_at": "2024-05-15T00:00:00Z",
  "updated_at": "2024-05-15T00:00:00Z"
}
```

#### GET `/referrals/`
List referrals accessible to current user.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (integer, default: 0)
- `limit` (integer, default: 100)
- `status` (string, optional)
- `priority` (string, optional)
- `patient_id` (integer, optional)

**Response:**
```json
[
  {
    "id": 1,
    "patient_name": "Jane Smith",
    "from_facility_name": "Kenyatta National Hospital",
    "to_facility_name": "Moi Teaching and Referral Hospital",
    "status": "submitted",
    "priority": "high",
    "created_at": "2024-05-15T00:00:00Z"
  }
]
```

#### GET `/referrals/{referral_id}`
Get referral by ID with full details.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": 1,
  "patient_id": 1,
  "from_facility_id": 1,
  "to_facility_id": 2,
  "created_by": 1,
  "priority": "high",
  "status": "submitted",
  "reason_for_referral": "Suspected cardiac arrhythmia requiring specialist evaluation",
  "clinical_notes": "Patient presents with palpitations, shortness of breath, and chest discomfort. ECG confirms intermittent atrial fibrillation.",
  "ai_summary": "45-year-old male presenting with chest pain and shortness of breath...",
  "ai_status": "completed",
  "notes": null,
  "created_at": "2024-05-15T00:00:00Z",
  "updated_at": "2024-05-15T00:00:00Z",
  "patient": {
    "id": 1,
    "first_name": "Jane",
    "last_name": "Smith",
    "date_of_birth": "1985-03-15",
    "gender": "female"
  },
  "from_facility": {
    "id": 1,
    "name": "Kenyatta National Hospital",
    "facility_code": "KNH"
  },
  "to_facility": {
    "id": 2,
    "name": "Moi Teaching and Referral Hospital",
    "facility_code": "MTRH"
  },
  "creator": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe"
  },
  "documents": [],
  "voice_notes": []
}
```

#### PUT `/referrals/{referral_id}`
Update referral details.

**Headers:** `Authorization: Bearer <token>`

**Request Body:** (All fields optional)
```json
{
  "priority": "emergency",
  "clinical_notes": "Updated clinical notes with additional information."
}
```

**Response:** Same as POST `/referrals/` response

#### POST `/referrals/{referral_id}/submit`
Submit a draft referral.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Referral submitted successfully"
}
```

---

## Documents

### Endpoints

#### POST `/documents/upload`
Upload a document for a referral.

**Headers:** `Authorization: Bearer <token>`

**Request:** `multipart/form-data`
- `file` - Document file (PDF, images)
- `referral_id` - Referral ID
- `document_type` - Type of document

**Response:**
```json
{
  "id": 1,
  "file_name": "lab_results.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000,
  "referral_id": 1,
  "created_at": "2024-05-15T00:00:00Z"
}
```

#### GET `/documents/referral/{referral_id}`
Get documents for a referral.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "id": 1,
    "file_name": "lab_results.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000,
    "referral_id": 1,
    "created_at": "2024-05-15T00:00:00Z"
  }
]
```

---

## Voice Notes

### Endpoints

#### POST `/voice-notes/upload`
Upload a voice note for a referral.

**Headers:** `Authorization: Bearer <token>`

**Request:** `multipart/form-data`
- `audio_file` - Audio file (WAV, MP3, M4A)
- `referral_id` - Referral ID

**Response:**
```json
{
  "id": 1,
  "audio_file_name": "clinical_notes.wav",
  "duration_seconds": 120,
  "transcript": "Patient presents with chest pain and shortness of breath...",
  "status": "completed",
  "referral_id": 1,
  "created_at": "2024-05-15T00:00:00Z"
}
```

#### GET `/voice-notes/referral/{referral_id}`
Get voice notes for a referral.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "id": 1,
    "audio_file_name": "clinical_notes.wav",
    "duration_seconds": 120,
    "transcript": "Patient presents with chest pain and shortness of breath...",
    "status": "completed",
    "referral_id": 1,
    "created_at": "2024-05-15T00:00:00Z"
  }
]
```

---

## AI Services

### Endpoints

#### POST `/ai/test-summary`
Test AI referral summary generation (development endpoint).

**Headers:** `Authorization: Bearer <token>`

**Permissions:** Super Admin, Facility Admin, Clinician only

**Request Body:**
```json
{
  "patient_name": "Jane Smith",
  "age": "45",
  "gender": "female",
  "date_of_birth": "1979-03-15",
  "allergies": "Penicillin, Shellfish",
  "medications": "Lisinopril 10mg daily, Metformin 500mg twice daily",
  "chronic_conditions": "Hypertension, Type 2 Diabetes",
  "reason_for_referral": "Suspected cardiac arrhythmia requiring specialist evaluation",
  "priority": "high",
  "from_facility": "Kenyatta National Hospital",
  "to_facility": "Moi Teaching and Referral Hospital",
  "clinical_notes": "Patient presents with palpitations, shortness of breath, and chest discomfort. ECG confirms intermittent atrial fibrillation.",
  "documents_summary": "Lab results show elevated troponin levels. ECG attached.",
  "voice_transcripts": "No voice notes provided",
  "created_at": "2024-05-15T10:30:00Z",
  "status": "submitted"
}
```

**Response:**
```json
{
  "success": true,
  "context": {
    "patient_name": "Jane Smith",
    "age": "45",
    "gender": "female",
    "date_of_birth": "1979-03-15",
    "allergies": "Penicillin, Shellfish",
    "medications": "Lisinopril 10mg daily, Metformin 500mg twice daily",
    "chronic_conditions": "Hypertension, Type 2 Diabetes",
    "reason_for_referral": "Suspected cardiac arrhythmia requiring specialist evaluation",
    "priority": "high",
    "from_facility": "Kenyatta National Hospital",
    "to_facility": "Moi Teaching and Referral Hospital",
    "clinical_notes": "Patient presents with palpitations, shortness of breath, and chest discomfort. ECG confirms intermittent atrial fibrillation.",
    "documents_summary": "Lab results show elevated troponin levels. ECG attached.",
    "voice_transcripts": "No voice notes provided",
    "created_at": "2024-05-15T10:30:00Z",
    "status": "submitted"
  },
  "ai_summary": {
    "summary": "45-year-old female presenting with palpitations, shortness of breath, and chest discomfort. ECG confirms intermittent atrial fibrillation. History of hypertension and type 2 diabetes.",
    "key_findings": [
      "Intermittent atrial fibrillation confirmed on ECG",
      "Hypertension and type 2 diabetes as comorbidities",
      "Elevated troponin levels on lab results",
      "Symptoms include palpitations, dyspnea, chest discomfort"
    ],
    "risks": [
      "Potential for thromboembolic events due to AFib",
      "Cardiac decompensation risk with comorbidities",
      "Possible acute coronary syndrome given elevated troponin"
    ],
    "missing_info": [
      "Current vital signs (BP, HR, O2 saturation)",
      "Complete cardiac enzyme panel",
      "Echocardiogram results",
      "Current anticoagulation status"
    ],
    "recommendations": [
      "Urgent cardiac evaluation within 24 hours",
      "Consider anticoagulation therapy assessment",
      "Complete cardiac workup including echocardiogram",
      "Optimize blood pressure and glucose control"
    ],
    "completeness_score": 65,
    "urgency_level": "High"
  },
  "tested_by": "admin@mediflow.com",
  "test_timestamp": "2024-05-15 10:30:45"
}
```

#### POST `/ai/test-transcription`
Test AI transcription cleanup (development endpoint).

**Headers:** `Authorization: Bearer <token>`

**Permissions:** Super Admin, Facility Admin, Clinician only

**Request Body:**
```json
{
  "raw_transcript": "um the patient came in with like chest pain and uh shortness of breath they said it feels like pressure um they have a history of hypertension and diabetes",
  "patient_name": "Jane Smith",
  "referral_reason": "Suspected cardiac arrhythmia",
  "specialty": "Cardiology"
}
```

**Response:**
```json
{
  "success": true,
  "context": {
    "raw_transcript": "um the patient came in with like chest pain and uh shortness of breath they said it feels like pressure um they have a history of hypertension and diabetes",
    "patient_name": "Jane Smith",
    "referral_reason": "Suspected cardiac arrhythmia",
    "specialty": "Cardiology"
  },
  "cleaned_transcript": "The patient presented with chest pain and shortness of breath. They described the chest pain as pressure-like. The patient has a medical history of hypertension and diabetes.",
  "tested_by": "admin@mediflow.com",
  "test_timestamp": "2024-05-15 10:30:45"
}
```

#### POST `/ai/test-document-extraction`
Test AI document information extraction (development endpoint).

**Headers:** `Authorization: Bearer <token>`

**Permissions:** Super Admin, Facility Admin, Clinician only

**Request Body:**
```json
{
  "document_type": "lab_report",
  "document_text": "Patient: Jane Smith\nDate: 2024-05-15\nTroponin I: 0.15 ng/mL (elevated)\nCK-MB: 25 U/L (normal)\nBNP: 450 pg/mL (elevated)\nGlucose: 180 mg/dL (elevated)",
  "patient_name": "Jane Smith",
  "age": "45",
  "gender": "female"
}
```

**Response:**
```json
{
  "success": true,
  "context": {
    "document_type": "lab_report",
    "document_text": "Patient: Jane Smith\nDate: 2024-05-15\nTroponin I: 0.15 ng/mL (elevated)\nCK-MB: 25 U/L (normal)\nBNP: 450 pg/mL (elevated)\nGlucose: 180 mg/dL (elevated)",
    "patient_name": "Jane Smith",
    "age": "45",
    "gender": "female"
  },
  "extracted_info": {
    "patient_name": "Jane Smith",
    "document_date": "2024-05-15",
    "lab_values": [
      {
        "test": "Troponin I",
        "value": "0.15 ng/mL",
        "status": "elevated"
      },
      {
        "test": "CK-MB",
        "value": "25 U/L",
        "status": "normal"
      },
      {
        "test": "BNP",
        "value": "450 pg/mL",
        "status": "elevated"
      },
      {
        "test": "Glucose",
        "value": "180 mg/dL",
        "status": "elevated"
      }
    ],
    "summary": "Lab results show elevated troponin I and BNP, indicating possible cardiac stress. Glucose is elevated, suggesting poor glycemic control."
  },
  "tested_by": "admin@mediflow.com",
  "test_timestamp": "2024-05-15 10:30:45"
}
```

#### POST `/ai/referral/{referral_id}/summarize`
Generate AI-powered referral summary for an existing referral.

**Headers:** `Authorization: Bearer <token>`

**URL Parameters:**
- `referral_id` (integer, required) - ID of the referral to summarize

**Permissions:** Users with referral access permissions

**Response:**
```json
{
  "success": true,
  "referral_id": 1,
  "ai_summary": {
    "summary": "45-year-old male presenting with chest pain and shortness of breath, referred for cardiac evaluation. ECG shows possible abnormal rhythm.",
    "key_findings": [
      "Chest pain described as pressure-like, 2/10 severity",
      "Shortness of breath on minimal exertion",
      "ECG indicates sinus arrhythmia",
      "History of hypertension controlled with medication"
    ],
    "risks": [
      "Potential cardiac instability requiring urgent evaluation",
      "Hypertension as underlying risk factor",
      "Possible progression to acute cardiac event"
    ],
    "missing_info": [
      "Current vital signs (BP, heart rate, oxygen saturation)",
      "Cardiac enzymes (troponin, CK-MB)",
      "Previous ECG comparisons",
      "Current medication adherence"
    ],
    "recommendations": [
      "Urgent cardiac evaluation within 24 hours",
      "Complete cardiac workup including enzymes and imaging",
      "Blood pressure optimization",
      "Consider stress testing based on evaluation"
    ],
    "completeness_score": 60,
    "urgency_level": "High"
  },
  "updated_by": "clinician@mediflow.com",
  "updated_at": "2024-05-15 10:30:45"
}
```

**Note:** This endpoint automatically updates the referral's `ai_summary` and `ai_status` fields in the database.

#### GET `/ai/status`
Get AI service status and configuration.

**Headers:** `Authorization: Bearer <token>`

**Permissions:** Super Admin, Facility Admin only

**Response:**
```json
{
  "ai_service_available": true,
  "openai_api_key_configured": true,
  "whisper_model": "large-v3",
  "supported_operations": [
    "referral_summarization",
    "transcription_cleanup",
    "document_extraction",
    "missing_info_assessment",
    "risk_assessment"
  ],
  "prompt_templates_available": [
    "referral_summary",
    "transcription_cleanup",
    "document_extraction",
    "missing_info",
    "risk_assessment"
  ],
  "medical_safety_features": [
    "disclaimer_inclusion",
    "uncertainty_handling",
    "risk_flagging",
    "missing_info_identification"
  ],
  "service_dependencies": {
    "ai_service": "services/ai_service.py",
    "prompt_builder": "utils/ai_prompts.py",
    "text_cleaning": "utils/text_cleaning.py",
    "audio_processing": "utils/audio_utils.py"
  }
}
```

#### GET `/ai/health`
Simple health check for AI service (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "service": "mediflow-ai",
  "timestamp": "2024-05-15 10:30:45",
  "mock_mode": false
}
```

**Note:** This endpoint can be used for monitoring and load balancing without authentication.

---

## WebSocket

### Connection
**URL:** `ws://localhost:8000/api/v1/websocket/ws`

### Authentication
Query parameter: `token=<jwt_token>`

### Message Format
```json
{
  "type": "notification",
  "data": {
    "id": 1,
    "title": "New Referral Received",
    "message": "A new referral has been assigned to your facility",
    "priority": "high",
    "created_at": "2024-05-15T00:00:00Z"
  }
}
```

---

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error message description"
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

---

## Data Validation

### Required Fields
- **Patient Creation**: first_name, last_name, date_of_birth, gender, phone
- **Referral Creation**: patient_id, to_facility_id, priority
- **User Creation**: first_name, last_name, email, password, role
- **Facility Creation**: name, facility_code, type, level, county

### Field Formats
- **Email**: Valid email format
- **Phone**: International format (+254...)
- **Date**: ISO 8601 format (YYYY-MM-DD)
- **DateTime**: ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)

---

## MRN Format

Medical Record Numbers are automatically generated in the format:
```
{FACILITY_CODE}-{YEAR}-{SEQUENTIAL_NUMBER}-{CHECK_DIGIT}
```

Example: `KNH-2024-0001-7`

---

## AI Integration Notes

### AI Summary Structure
AI summaries include:
- **Quality Score** (1-10)
- **Patient Summary** - Brief clinical overview
- **Missing Information** - Critical data gaps
- **Risk Factors** - Identified clinical risks
- **Recommendations** - Suggested actions

### Voice Transcription
- **Google Speech Recognition** (free, web-based API)
- **Automatic transcription** on voice note upload
- **Medical terminology correction** via AI cleanup
- **Processed transcript** stored in `processed_transcript` field
- **AI summary** generated from cleaned transcript

### Document Processing
- **PDF text extraction** using pdfplumber and PyMuPDF
- **OCR for scanned documents** using Tesseract
- **Image preprocessing** with OpenCV for better OCR accuracy
- **Structured medical data extraction** (vitals, medications, diagnoses)
- **Extracted text** stored in `extracted_text` field
- **AI processing status** tracked with `ai_processed` flag

### AI Workflow for Referrals

#### How AI Summary Works

**Automatic AI Processing:**
When a referral is created or updated with clinical information, the system automatically triggers AI processing to generate a comprehensive summary.

**AI Processing Flow:**
```
1. Referral Created/Updated
   ↓
2. System collects context:
   - Patient information (demographics, medical history, allergies, medications)
   - Referral details (reason, clinical notes, priority)
   - Facility information (sender, receiver)
   - Attached documents (summaries)
   - Voice notes (transcripts)
   ↓
3. AI Service (Groq Llama 3.1 8B) processes context
   ↓
4. Structured AI response generated:
   - SUMMARY: Clinical overview
   - KEY CLINICAL FINDINGS: Important observations
   - KEY RISKS: Identified risks
   - MISSING CRITICAL INFORMATION: Data gaps
   - RECOMMENDED NEXT STEPS: Action items
   - UNCERTAINTY LEVEL: Confidence assessment
   - MEDICAL SAFETY NOTE: Disclaimer
   ↓
5. Referral updated with:
   - ai_summary: Main summary text
   - ai_status: "completed" or "failed"
   - notes: Additional AI metadata
```

**Frontend Integration:**

**When Creating a Referral:**
```typescript
// Create referral - AI processing happens automatically
POST /api/v1/referrals/
{
  "patient_id": 1,
  "to_facility_id": 2,
  "priority": "high",
  "reason_for_referral": "Suspected cardiac arrhythmia",
  "clinical_notes": "Patient presents with palpitations..."
}

// Response includes AI status
{
  "id": 1,
  "ai_summary": null,           // Initially null
  "ai_status": "processing",  // AI processing in progress
  ...
}
```

**Monitoring AI Processing:**
```typescript
// Poll for AI completion
GET /api/v1/referrals/{referral_id}

// Check ai_status field:
// - "processing": AI is working
// - "completed": AI summary ready
// - "failed": AI processing failed
// - null: Not yet triggered
```

**AI Summary Response:**
```typescript
{
  "ai_summary": "45-year-old male presenting with chest pain and shortness of breath, referred for cardiac evaluation. ECG shows possible abnormal rhythm.",
  "ai_status": "completed",
  "notes": "AI-generated summary using Groq Llama 3.1 8B"
}
```

**AI Configuration:**
- **Provider**: Groq (fast inference)
- **Model**: Llama 3.1 8B Instruct
- **Fallback**: Mock responses if API not configured
- **Processing Time**: 2-5 seconds typically
- **Reliability**: Automatic retry on failure

**Document AI Processing:**

When documents are uploaded:
```typescript
POST /api/v1/documents/upload
{
  "file": <binary>,
  "referral_id": 1,
  "document_type": "lab_results"
}

// Response includes AI status
{
  "id": 1,
  "extracted_text": "Lab results show...",  // OCR/Text extraction
  "ai_processed": true,                     // AI analysis complete
  "ai_summary": "Key findings: ..."         // Structured extraction
}
```

**Voice Note AI Processing:**

When voice notes are uploaded:
```typescript
POST /api/v1/voice-notes/upload
{
  "audio_file": <binary>,
  "referral_id": 1
}

// Response includes transcription status
{
  "id": 1,
  "transcript": "Patient presents with...",           // Raw transcription
  "processed_transcript": "Patient presents with...", // AI-cleaned
  "ai_summary": "Key clinical points: ...",          // AI summary
  "status": "completed"
}
```

**AI Service Status Check:**
```typescript
GET /api/v1/ai/status

// Response
{
  "text_ai": {
    "provider": "Groq",
    "model": "llama-3.1-8b-instant",
    "is_configured": true,
    "capabilities": ["Medical summarization", "Clinical reasoning", "Risk assessment"]
  },
  "speech_ai": {
    "provider": "Google Speech Recognition",
    "is_configured": true
  },
  "document_ai": {
    "provider": "Tesseract + PDF Libraries",
    "tesseract_available": true,
    "is_configured": true
  }
}
```

**Important Notes for Frontend:**
1. AI processing is **automatic** - no separate API call needed
2. AI processing is **asynchronous** - may take 2-5 seconds
3. **Poll the referral endpoint** to check AI completion status
4. **Handle AI failures gracefully** - system continues without AI
5. **Display AI summaries** as supplementary information, not primary
6. **Always include medical disclaimer** when showing AI-generated content

---

## Permissions

### Role-Based Access
- **Super Admin**: Full system access
- **Facility Admin**: Facility-specific administration
- **Clinician**: Patient and referral management within facility
- **Patient**: Limited personal information access

### Facility-Based Filtering
- Users automatically filtered to their assigned facility
- Super admins see all facilities
- Cross-facility access requires appropriate permissions

---

## Rate Limiting

Currently no rate limiting implemented. Consider adding for production deployment.

---

## CORS Configuration

Configure CORS in `app/core/config.py` to allow frontend domain access.

---

## Testing

### Test Credentials
- **Super Admin**: admin@mediflow.com / admin123
- **Test Facility**: KNH (Kenyatta National Hospital)

### Test Data
Use provided test data scripts to populate database with sample patients, users, and referrals.

---

## Deployment Notes

### Environment Variables

**Database & Security:**
- `DATABASE_URL` - PostgreSQL connection string (or SQLite for development)
- `SECRET_KEY` - JWT secret key for token signing
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token lifetime (default: 30)
- `ALGORITHM` - JWT algorithm (default: HS256)

**Refresh Token Configuration:**
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token lifetime (default: 7)

**SMTP Email Configuration (Google SMTP):**
- `SMTP_HOST` - SMTP server host (default: smtp.gmail.com)
- `SMTP_PORT` - SMTP server port (default: 587)
- `SMTP_USER` - SMTP username (email address)
- `SMTP_PASSWORD` - SMTP password (use App Password for Gmail)
- `SMTP_FROM_EMAIL` - From email address
- `SMTP_FROM_NAME` - From name (default: MediFlow)
- `SMTP_USE_TLS` - Use TLS (default: true)

**AI Configuration:**
- `GROQ_API_KEY` - Groq AI API key for Llama 3.1 8B
- `OPENAI_API_KEY` - OpenAI API key (optional, for Whisper)
- `WHISPER_MODEL` - Whisper model name (default: large-v3)
- `TESSERACT_PATH` - Tesseract OCR path (Windows: C:\Program Files\Tesseract-OCR\tesseract.exe)

**File Storage:**
- `UPLOAD_DIR` - Upload directory (default: uploads)
- `MAX_FILE_SIZE` - Maximum file size in bytes (default: 10485760)

### Recent System Updates

**Authentication Enhancements:**
- ✅ Refresh token implementation for seamless user sessions
- ✅ Login now returns both access_token and refresh_token
- ✅ Refresh token endpoint to obtain new access tokens
- ✅ Refresh tokens stored in database with revocation support
- ✅ 7-day refresh token lifetime configurable

**Email Service Improvements:**
- ✅ SMTP configuration for Google Gmail integration
- ✅ Professional HTML email templates
- ✅ Email verification for new users
- ✅ Password reset with email delivery
- ✅ Demo mode fallback when SMTP not configured

**AI System Integration:**
- ✅ Automatic AI summary generation on referral creation
- ✅ Groq Llama 3.1 8B for medical summarization
- ✅ Fallback to mock responses when AI unavailable
- ✅ AI status tracking (processing, completed, failed)
- ✅ Document OCR and text extraction
- ✅ Voice note transcription with AI cleanup

**Database Compatibility Fixes (May 2026):**
- ✅ Fixed SQLite compatibility issue with NOW() function
- ✅ Replaced PostgreSQL-specific `NOW()` with SQLite-compatible `datetime('now')`
- ✅ Affected AI endpoints: test-summary, test-transcription, test-document-extraction, referral/summarize, health
- ✅ System now supports both PostgreSQL and SQLite databases

### Database Migrations
Run Alembic migrations:
```bash
alembic upgrade head
```

---

## Support

For integration issues, contact the backend development team with:
- API endpoint being called
- Request payload
- Response received
- Error messages (if any)

---

## Version Information

- **API Version**: v1
- **Backend Framework**: FastAPI
- **Python Version**: 3.11+
- **Database**: PostgreSQL

---

## Future Enhancements

Planned features for future releases:
- Real-time referral tracking
- Advanced AI diagnostics
- Mobile app integration
- Telemedicine integration
- Analytics dashboard
- Advanced reporting
# 🏥 MediFlow Backend System Documentation

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture](#architecture)
4. [Core Features](#core-features)
5. [API Endpoints](#api-endpoints)
6. [Database Schema](#database-schema)
7. [AI Integration](#ai-integration)
8. [Security & Authentication](#security--authentication)
9. [Audit & Compliance](#audit--compliance)
10. [Configuration](#configuration)
11. [Development Setup](#development-setup)
12. [Deployment](#deployment)
13. [Testing](#testing)
14. [Future Enhancements](#future-enhancements)

---

## 🎯 System Overview

MediFlow is a premium healthcare SaaS platform backend that provides comprehensive referral management, AI-powered medical document processing, and secure healthcare data management. The system is designed to serve three primary user roles: Super Admins, Facility Admins, and Clinicians.

### 🏗️ Core Purpose
- **Referral Management**: Streamline patient referrals between healthcare facilities
- **AI-Powered Processing**: Automated transcription, OCR, and medical summarization
- **Secure Healthcare Data**: HIPAA-compliant data handling and audit trails
- **Multi-Tenant Architecture**: Support for multiple healthcare facilities
- **Real-time Collaboration**: Secure communication and document sharing

---

## 🛠️ Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Python 3.11**: Core programming language
- **Uvicorn**: ASGI server for production deployment

### Database & ORM
- **PostgreSQL**: Primary database for relational data
- **SQLAlchemy**: Python SQL toolkit and ORM
- **Alembic**: Database migration tool

### Authentication & Security
- **JWT (JSON Web Tokens)**: Stateless authentication with refresh tokens
- **bcrypt**: Password hashing with salt rounds
- **Role-based Access Control (RBAC)**: Granular permissions
- **Email Verification**: Prevent fake accounts with email verification
- **Password Reset Flow**: Secure password recovery with token-based reset
- **Email Service**: Professional HTML email templates with SMTP integration

### AI & Machine Learning
- **Groq (Llama 3.1 8B)**: Text summarization and reasoning
- **Google Speech Recognition**: Speech-to-text transcription (free, web-based API)
- **Tesseract OCR**: Document text extraction
- **pdfplumber & PyMuPDF**: PDF processing

### File Processing
- **PyAudio**: Audio processing for speech recognition
- **OpenCV**: Image preprocessing for OCR
- **Pillow (PIL)**: Image manipulation

### Development Tools
- **Pydantic**: Data validation and serialization
- **pytest**: Testing framework
- **Black**: Code formatting
- **mypy**: Type checking

---

## 🏗️ Architecture

### Layered Architecture
```
┌─────────────────────────────────────────┐
│           API Layer (FastAPI)           │
├─────────────────────────────────────────┤
│         Business Logic Layer            │
│  ┌─────────────┐ ┌─────────────────────┐ │
│  │   Services  │ │    AI Services      │ │
│  └─────────────┘ └─────────────────────┘ │
├─────────────────────────────────────────┤
│           Data Access Layer             │
│  ┌─────────────┐ ┌─────────────────────┐ │
│  │   Models    │ │   Database (PG)     │ │
│  └─────────────┘ └─────────────────────┘ │
├─────────────────────────────────────────┤
│         Infrastructure Layer             │
│  ┌─────────────┐ ┌─────────────────────┐ │
│  │   Utils     │ │   File Storage      │ │
│  └─────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────┘
```

### Service Architecture
- **Modular Services**: Each business domain has dedicated service classes
- **AI Services**: Separate services for text, speech, and document AI
- **Dependency Injection**: Clean separation of concerns
- **Async Processing**: Non-blocking AI operations

---

## 🌟 Core Features

### 1. User Management & Authentication
- **Multi-role Authentication**: Super Admin, Facility Admin, Clinician
- **JWT with Refresh Tokens**: Secure, stateless authentication with 30min access tokens
- **Email Verification**: Professional HTML email templates with verification links
- **Password Reset Flow**: Token-based password reset with secure email delivery
- **Session Management**: Secure session handling with audit logging
- **Welcome Emails**: Automated onboarding emails for new users

### 2. Facility Management
- **Multi-tenant Support**: Multiple healthcare facilities
- **Hierarchical Access**: Facility-scoped data access
- **Facility Configuration**: Customizable facility settings
- **User Assignment**: Assign users to specific facilities

### 3. Patient Management
- **Comprehensive Patient Records**: Demographics, medical history
- **MRN Generation**: Automatic Medical Record Number generation
- **Patient Identifiers**: Multiple identifier support
- **Privacy Controls**: HIPAA-compliant data handling

### 4. Referral System
- **End-to-End Referral Workflow**: Create → Send → Receive → Complete
- **AI-Powered Summaries**: Automated clinical summarization
- **Document Attachment**: Upload medical documents
- **Voice Notes**: Audio recordings with transcription
- **Status Tracking**: Real-time referral status updates
- **Priority Management**: Emergency, high, medium, low priority

### 5. AI Integration
- **Text AI (Groq Llama 3.1)**:
  - Medical document summarization
  - Clinical reasoning and analysis
  - Risk assessment
  - Missing information detection
  
- **Speech AI (Whisper Large-v3)**:
  - Medical dictation transcription
  - Audio preprocessing (noise reduction, normalization)
  - Chunked processing for long recordings
  - Word-level timestamps and confidence scores
  
- **Document AI (OCR)**:
  - PDF text extraction (digital and scanned)
  - Image preprocessing for optimal OCR
  - Structured medical data extraction
  - Multi-format support (PDF, images)

### 6. Document Management
- **Secure File Upload**: Encrypted file storage
- **Multiple File Types**: PDF, images, audio files
- **AI Processing**: Automatic text extraction and analysis
- **Version Control**: Track document versions
- **Access Control**: Role-based document access

### 7. Voice Notes
- **Audio Recording**: Upload voice recordings
- **AI Transcription**: Automatic speech-to-text
- **Quality Assessment**: Audio quality metrics
- **Speaker Diarization**: Identify different speakers
- **Medical Dictation**: Optimized for medical terminology

### 8. Audit & Compliance
- **Comprehensive Audit Trail**: Log all system actions
- **Role-based Access**: Different access levels for audit logs
- **Export Capabilities**: CSV/JSON export for compliance
- **Compliance Reporting**: Generate compliance reports
- **Data Retention**: Configurable data retention policies

---

## 🛡️ API Endpoints

### Authentication (`/api/v1/auth/`)
```
POST /register             # User registration
POST /login                # User login
POST /logout               # User logout
POST /forgot-password      # Password reset request
POST /reset-password       # Password reset with token
POST /verify-email         # Email verification
POST /resend-verification  # Resend verification email
POST /verify-code          # Verify verification code
POST /refresh-token        # Refresh access token
GET  /me                  # Current user info
POST /change-password     # Change password
```

### Users (`/api/v1/users/`)
```
GET    /               # List users (admin only)
GET    /{id}          # Get user details
PUT    /{id}          # Update user
DELETE /{id}          # Delete user
POST   /{id}/activate # Activate/deactivate user
```

### Facilities (`/api/v1/facilities/`)
```
GET    /               # List facilities
POST   /               # Create facility
GET    /{id}          # Get facility details
PUT    /{id}          # Update facility
DELETE /{id}          # Delete facility
```

### Patients (`/api/v1/patients/`)
```
GET    /               # List patients
POST   /               # Create patient
GET    /{id}          # Get patient details
PUT    /{id}          # Update patient
DELETE /{id}          # Delete patient
POST   /{id}/identifiers # Add patient identifier
```

### Referrals (`/api/v1/referrals/`)
```
GET    /               # List referrals
POST   /               # Create referral
GET    /{id}          # Get referral details
PUT    /{id}          # Update referral
POST   /{id}/accept   # Accept referral
POST   /{id}/reject   # Reject referral
POST   /{id}/summarize # Generate AI summary
```

### Documents (`/api/v1/documents/`)
```
POST   /upload        # Upload document
GET    /{id}          # Get document
DELETE /{id}          # Delete document
POST   /{id}/extract  # Extract text with AI
```

### Voice Notes (`/api/v1/voice-notes/`)
```
POST   /upload        # Upload voice note
GET    /{id}          # Get voice note
PUT    /{id}          # Update voice note
POST   /{id}/transcribe # Transcribe with AI
```

### AI Services (`/api/v1/ai/`)
```
POST   /test-summary     # Test AI summarization
POST   /test-transcription # Test AI transcription
POST   /test-document-extraction # Test AI OCR
GET    /status           # AI service status
GET    /health           # Health check
```

### Audit (`/api/v1/audit/`)
```
GET    /logs          # View audit logs
GET    /logs/{id}     # Get specific audit log
GET    /logs/summary  # Audit summary statistics
GET    /export        # Export audit logs
```

---

## 🗄️ Database Schema

### Core Tables

#### Users
```sql
users:
- id (PK)
- first_name
- last_name
- email (unique)
- password_hash
- role (enum: super_admin, facility_admin, clinician)
- facility_id (FK, nullable)
- is_active
- email_verified
- created_at
- updated_at

password_reset_tokens:
- id (PK)
- user_id (FK)
- token (unique)
- created_at
- expires_at
- is_used

email_verification_tokens:
- id (PK)
- user_id (FK)
- email
- token (unique)
- created_at
- expires_at
- is_verified
```

#### Facilities
```sql
facilities:
- id (PK)
- name
- code (unique)
- type (enum: hospital, clinic, health_center)
- level (enum: level_1-6)
- address
- phone
- email
- is_active
- created_at
- updated_at
```

#### Patients
```sql
patients:
- id (PK)
- first_name
- last_name
- date_of_birth
- gender
- phone
- email
- address
- created_at
- updated_at

patient_identifiers:
- id (PK)
- patient_id (FK)
- identifier_type
- identifier_value
- facility_id (FK)
- is_primary
- created_at
```

#### Referrals
```sql
referrals:
- id (PK)
- patient_id (FK)
- from_facility_id (FK)
- to_facility_id (FK)
- created_by (FK)
- priority (enum: low, medium, high, emergency)
- status (enum: draft, submitted, accepted, in_transit, received, completed, rejected)
- reason_for_referral
- clinical_notes
- ai_summary
- created_at
- updated_at
```

#### Documents
```sql
referral_documents:
- id (PK)
- referral_id (FK)
- uploaded_by (FK)
- file_type (enum: lab_report, discharge_summary, prescription, imaging, referral_note, other)
- file_path
- file_name
- file_size
- mime_type
- extracted_text
- ai_processed
- created_at
```

#### Voice Notes
```sql
voice_notes:
- id (PK)
- referral_id (FK)
- uploaded_by (FK)
- audio_path
- transcription
- confidence_score
- duration_seconds
- word_count
- status (enum: uploaded, processing, transcribed, failed)
- created_at
```

#### Audit Logs
```sql
audit_logs:
- id (PK)
- user_id (FK, nullable)
- action (enum: create, update, delete, login, logout, upload, download, view, password_reset, email_verification)
- entity_type
- entity_id
- details (JSON)
- ip_address
- user_agent
- created_at
```

---

## 🤖 AI Integration Details

### Text AI Service (Groq Llama 3.1 8B)
```python
# Capabilities:
- Medical document summarization
- Clinical reasoning and analysis
- Risk assessment and flagging
- Missing information detection
- Structured medical data extraction

# Configuration:
- Model: llama-3.1-8b-instant
- Provider: Groq
- Response format: Structured JSON
- Context window: 8192 tokens
```

### Speech AI Service (Whisper Large-v3)
```python
# Capabilities:
- Medical dictation transcription
- Multi-language support
- Word-level timestamps
- Confidence scoring
- Speaker diarization

# Optimization:
- Audio preprocessing (noise reduction, normalization)
- Chunked processing for long recordings
- 16kHz mono conversion
- Beam search for accuracy
```

### Document AI Service (OCR)
```python
# Capabilities:
- PDF text extraction (digital and scanned)
- Image OCR with preprocessing
- Structured medical data extraction
- Multiple format support

# Technologies:
- pdfplumber: Digital PDF extraction
- PyMuPDF: Advanced PDF processing
- Tesseract OCR: Scanned document processing
- OpenCV: Image preprocessing
```

---

## 🔐 Security & Authentication

### Authentication Flow
1. **User Login**: Email/password → JWT access + refresh tokens
2. **Token Validation**: Bearer token verification on each request
3. **Role-based Access**: Check user permissions for resources
4. **Token Refresh**: Automatic token refresh using refresh token
5. **Session Security**: Secure token storage and validation

### Security Features
- **Password Hashing**: bcrypt with salt rounds
- **JWT Security**: Short-lived access tokens (30 min)
- **Refresh Tokens**: Long-lived refresh tokens (30 days)
- **Rate Limiting**: Prevent brute force attacks
- **CORS Protection**: Cross-origin request security
- **Input Validation**: Pydantic model validation
- **SQL Injection Prevention**: SQLAlchemy ORM protection

### Role-based Access Control (RBAC)
```python
# Permission Matrix:
┌─────────────┬──────────────┬──────────────┬──────────────┐
│   Resource  │ Super Admin  │Facility Admin│  Clinician   │
├─────────────┼──────────────┼──────────────┼──────────────┤
│ All Users   │   CRUD       │  Facility    │     Own      │
│ Facilities  │   CRUD       │    Own       │    View      │
│ Patients    │   CRUD       │  Facility    │  Assigned    │
│ Referrals   │   CRUD       │  Facility    │  Assigned    │
│ Documents   │   CRUD       │  Facility    │  Assigned    │
│ Audit Logs  │   CRUD       │  Facility    │     None     │
└─────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 📊 Audit & Compliance

### Audit Logging
- **Comprehensive Logging**: All user actions automatically logged
- **Structured Data**: JSON-formatted audit entries
- **Context Information**: IP address, user agent, timestamps
- **Entity Tracking**: Track changes to specific entities
- **User Attribution**: Link actions to specific users

### Compliance Features
- **HIPAA Compliance**: Secure handling of protected health information
- **Data Retention**: Configurable data retention policies
- **Access Controls**: Role-based access to sensitive data
- **Audit Trails**: Complete audit trail for compliance reporting
- **Export Capabilities**: CSV/JSON export for compliance audits

### Audit Data Structure
```python
{
  "id": 12345,
  "user_id": 678,
  "action": "create",
  "entity_type": "referral",
  "entity_id": 456,
  "details": {
    "priority": "high",
    "patient_id": 789
  },
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## ⚙️ Configuration

### Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mediflow

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# File Storage
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760

# AI Services
GROQ_API_KEY=your-groq-api-key
OPENAI_API_KEY=your-openai-api-key
WHISPER_MODEL=large-v3
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# Email Service (NEW)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@mediflow.com
FROM_NAME=MediFlow Team

# CORS
ALLOWED_HOSTS=["*"]
```

### Configuration Classes
```python
# app/core/config.py
class Settings:
    # Database settings
    DATABASE_URL: str
    
    # Security settings
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # AI settings
    GROQ_API_KEY: str
    OPENAI_API_KEY: str
    WHISPER_MODEL: str = "large-v3"
    TESSERACT_PATH: str = ""
    
    # Email settings (NEW)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@mediflow.com"
    FROM_NAME: str = "MediFlow Team"
    
    # File settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024
```

---

## 🚀 Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis (optional, for caching)
- Tesseract OCR
- Git

### Installation Steps

1. **Clone Repository**
```bash
git clone <repository-url>
cd mediflow_backend
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup Database**
```bash
# Create PostgreSQL database
createdb mediflow

# Run migrations
alembic upgrade head
```

5. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. **Install Tesseract OCR**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

7. **Configure Email Service** (NEW)
```bash
# Set up email credentials in .env
cp .env.example .env
# Add your SMTP credentials:
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@mediflow.com
FROM_NAME=MediFlow Team

# For Gmail, use App Passwords: https://myaccount.google.com/apppasswords
```

8. **Start Development Server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Development Tools

#### Code Quality
```bash
# Code formatting
black app/

# Type checking
mypy app/

# Linting
flake8 app/
```

#### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_auth.py
```

#### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## 🚢 Deployment

### Production Deployment

#### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mediflow
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=mediflow
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

#### Environment Configuration
```bash
# Production environment variables
export DATABASE_URL="postgresql://user:pass@db:5432/mediflow"
export SECRET_KEY="production-secret-key"
export GROQ_API_KEY="production-groq-key"
export TESSERACT_PATH="/usr/bin/tesseract"
```

#### Health Checks
```bash
# Application health
curl http://localhost:8000/api/ai/health

# Database health
curl http://localhost:8000/api/ai/status
```

---

## 🧪 Testing

### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration
├── test_auth.py             # Authentication tests
├── test_users.py            # User management tests
├── test_facilities.py       # Facility tests
├── test_patients.py         # Patient tests
├── test_referrals.py        # Referral tests
├── test_documents.py        # Document tests
├── test_voice_notes.py      # Voice note tests
├── test_ai_services.py      # AI service tests
├── test_audit.py            # Audit tests
├── test_email_service.py    # Email service tests (NEW)
└── test_security.py        # Security tests (NEW)
```

### Test Categories

#### Unit Tests
- **Service Layer**: Test business logic in isolation
- **Model Tests**: Test database models and relationships
- **Utility Functions**: Test helper functions and utilities
- **Email Service**: Test email templates and SMTP integration (NEW)
- **Security Functions**: Test password hashing and token validation (NEW)

#### Integration Tests
- **API Endpoints**: Test HTTP endpoints and responses
- **Database Operations**: Test database interactions
- **AI Services**: Test AI service integrations
- **Email Delivery**: Test email sending and delivery (NEW)
- **Authentication Flow**: Test complete auth workflows (NEW)

#### End-to-End Tests
- **User Workflows**: Test complete user journeys
- **Referral Flow**: Test end-to-end referral process
- **AI Processing**: Test complete AI processing pipeline
- **Email Workflows**: Test password reset and verification flows (NEW)
- **Security Scenarios**: Test security event handling (NEW)

### Test Configuration
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db():
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

---

## 🔮 Future Enhancements

### Planned Features

#### Advanced AI Capabilities
- **Medical Entity Recognition**: Extract medical entities from text
- **Clinical Decision Support**: AI-powered treatment recommendations
- **Predictive Analytics**: Predict patient outcomes and risks
- **Natural Language Queries**: Query medical data using natural language

#### Enhanced Security
- **Multi-factor Authentication**: SMS/Email-based 2FA
- **Biometric Authentication**: Fingerprint/facial recognition
- **Advanced Encryption**: End-to-end encryption for sensitive data
- **Zero-knowledge Architecture**: Enhanced privacy protection
- **Real-time Threat Detection**: Automated security monitoring (NEW)

#### Performance Optimizations
- **Caching Layer**: Redis caching for frequently accessed data
- **Database Optimization**: Query optimization and indexing
- **Async Processing**: Background job processing with Celery
- **Load Balancing**: Horizontal scaling capabilities
- **Email Queue System**: Reliable email delivery with retry logic (NEW)

#### Integration Capabilities
- **HL7/FHIR Integration**: Healthcare data exchange standards
- **EHR Integration**: Connect with electronic health record systems
- **API Webhooks**: Real-time event notifications
- **Third-party Integrations: Connect with external healthcare services
- **Email Service Providers**: Integration with SendGrid, Mailgun (NEW)

#### Mobile & Real-time Features
- **Mobile API**: Optimized API for mobile applications
- **WebSocket Support**: Real-time notifications and updates
- **Push Notifications**: Mobile push notification support
- **Offline Support**: Offline-first mobile application support
- **Email Notifications**: Real-time email alerts and updates (NEW)

#### Analytics & Reporting
- **Advanced Analytics**: Machine learning-powered insights
- **Custom Reports**: User-configurable report generation
- **Data Visualization**: Interactive charts and dashboards
- **Export Options**: Multiple export formats (PDF, Excel, CSV)
- **Email Analytics**: Track email delivery and engagement (NEW)

#### Email & Communication Features
- **Email Templates**: Professional, customizable email templates
- **Email Campaigns**: Targeted healthcare communications
- **Appointment Reminders**: Automated email appointment reminders
- **Newsletter System**: Healthcare newsletter distribution
- **Multi-language Support**: Email templates in multiple languages

### Technical Debt & Improvements
- **Code Refactoring**: Improve code organization and maintainability
- **Test Coverage**: Increase test coverage to 90%+
- **Documentation**: Comprehensive API documentation
- **Performance Monitoring**: Application performance monitoring (APM)
- **Error Tracking**: Centralized error logging and tracking

---

## 📞 Support & Maintenance

### Monitoring & Logging
- **Application Logs**: Structured logging with ELK stack
- **Performance Metrics**: Application performance monitoring
- **Error Tracking**: Sentry for error tracking and alerting
- **Health Checks**: Regular health check endpoints

### Backup & Recovery
- **Database Backups**: Automated daily database backups
- **File Storage Backup**: Redundant file storage with backups
- **Disaster Recovery**: Disaster recovery plan and procedures
- **Data Retention**: Automated data cleanup and archiving

### Security Maintenance
- **Security Updates**: Regular dependency and security updates
- **Vulnerability Scanning**: Automated security vulnerability scanning
- **Penetration Testing**: Regular security penetration testing
- **Compliance Audits**: Regular compliance and security audits

---

## 📚 Additional Resources

### Documentation
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [ReDoc Documentation](http://localhost:8000/redoc) - Alternative API docs
- [Database Schema](./database_schema.md) - Detailed database schema
- [AI Integration Guide](./ai_integration.md) - AI service integration guide

### Development Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI framework docs
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/) - ORM documentation
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/) - Data validation docs

### Community & Support
- [GitHub Repository](https://github.com/your-org/mediflow-backend) - Source code repository
- [Issue Tracker](https://github.com/your-org/mediflow-backend/issues) - Bug reports and feature requests
- [Discord Community](https://discord.gg/mediflow) - Community discussion and support

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

We welcome contributions to the MediFlow project! Please see our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

---

*Last Updated: January 2024*
*Version: 1.0.0*

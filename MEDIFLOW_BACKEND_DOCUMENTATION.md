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

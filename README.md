# Mediflow Backend

**AI-Powered Healthcare Referral System API** for African facilities.

## Overview

Mediflow is an inter-facility patient referral management system with AI-assisted clinical summarization. It streamlines patient referrals between healthcare facilities by ensuring complete patient information transfer, reduced manual documentation effort, structured referral tracking, and AI-generated clinical summaries for receiving clinicians.

## Features

- **Multi-facility referrals** with real-time tracking
- **AI-powered summaries**, quality scores, and clinical suggestions
- **Voice-to-text transcription** for medical notes
- **Secure document management** with file uploads
- **Role-based authentication** (Super Admin/Facility Admin/Clinician/Patient)
- **MRN generation system** with concurrency safety
- **Comprehensive audit logging** for accountability
- **Facility-based data isolation** for security

## Architecture

- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: PostgreSQL with Alembic migrations
- **Authentication**: JWT-based with role-based access control (RBAC)
- **File Storage**: Local storage with organized structure
- **AI Integration**: Ready for OpenAI API and Whisper integration

## User Roles

1. **Super Admin**: System owner with full access
2. **Facility Admin**: Manages users and operations within their facility
3. **Clinician**: Creates patients, referrals, uploads documents and voice notes
4. **Patient**: (Future) Portal access to own referral information

## Core Modules

- **Authentication & Authorization**: JWT + RBAC system
- **Facility Management**: Multi-facility setup with levels and types
- **Patient Management**: Global patient records with facility-specific MRNs
- **Referral System**: Complete referral workflow with status tracking
- **Document System**: File uploads with type classification
- **Voice Notes**: Audio recording and transcription pipeline
- **Audit Logging**: Complete system activity tracking
- **MRN Generation**: Safe, concurrent Medical Record Number generation

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/mediflow_backend
cd mediflow_backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your database URL and secret key
```

5. **Set up database**
```bash
# Create database
createdb mediflow

# Run migrations
alembic upgrade head
```

6. **Start the server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

Create a `.env` file with:

```env
DATABASE_URL=postgresql://user:password@localhost/mediflow
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760  # 10MB
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Database Schema

The system uses the following main entities:

- **Users**: System actors with roles and facility assignments
- **Facilities**: Healthcare institutions with codes and levels
- **Patients**: Global patient records
- **Patient Identifiers**: MRN system linking patients to facilities
- **Referrals**: Clinical transfer workflow
- **Referral Documents**: Attached files
- **Voice Notes**: Audio recordings with transcripts
- **Audit Logs**: System activity tracking
- **Facility Counters**: MRN generation control

## MRN System

Each patient gets a facility-specific Medical Record Number (MRN):
- Format: `FACILITYCODE-00001` (e.g., `KNRH-00001`)
- Generated atomically to prevent duplicates
- Unique per facility
- Safe under concurrent access

## Security Features

- **JWT Authentication**: Secure token-based auth
- **Role-Based Access Control**: Granular permissions
- **Facility Isolation**: Data separation by facility
- **Audit Logging**: Complete activity tracking
- **Input Validation**: Pydantic schemas for all inputs

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
isort app/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Project Structure

```
mediflow_backend/
├── app/
│   ├── api/v1/endpoints/    # API routes
│   ├── core/                # Configuration and security
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── utils/               # Utility functions
│   ├── websocket/           # WebSocket connection manager
│   └── enums.py             # System enums
├── alembic/                 # Database migrations
├── uploads/                 # File storage (gitignored)
├── Dockerfile               # Production container image
├── docker-compose.yml       # Local development setup
├── render.yaml              # Render.com deployment config
├── gunicorn.conf.py         # Production server config
├── start.sh                 # Container entrypoint script
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
└── README.md                # This file
```

## Deployment

### Option 1: Docker Compose (Local / VPS)

```bash
# 1. Clone and configure
git clone https://github.com/paulathejennifer/mediflow_backend.git
cd mediflow_backend
cp .env.example .env
# Edit .env with your values

# 2. Build and run
docker-compose up --build -d

# 3. Access the API
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Option 2: Deploy to Render (Recommended)

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Blueprint**
4. Connect your GitHub repo
5. Render auto-detects `render.yaml` and creates:
   - Web service (Docker) with health checks
   - PostgreSQL database (free tier)
   - Persistent disk for file uploads
6. Add your API keys in the Render dashboard:
   - `GROQ_API_KEY` — get from [Groq Console](https://console.groq.com/keys)
   - `SMTP_USERNAME` / `SMTP_PASSWORD` — for email notifications

### Option 3: Docker Only

```bash
# Build the image
docker build -t mediflow-backend .

# Run with your own database
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/mediflow \
  -e SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))") \
  -e ENVIRONMENT=production \
  -v mediflow-uploads:/app/uploads \
  mediflow-backend
```

### Production Environment Variables

See [`.env.example`](.env.example) for the full list. Required variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key (auto-generated in dev) |
| `ENVIRONMENT` | `development` or `production` |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue on GitHub.

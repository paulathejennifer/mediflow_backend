# MediFlow Backend Setup Guide

This guide will help you set up and run the MediFlow backend for local development.

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Initial Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If you encounter issues with `openai-whisper` installation, it has been temporarily disabled in requirements.txt for development purposes.

## Database Setup

### SQLite (Development)

The project is configured to use SQLite for local development by default.

1. **Configure Environment Variables**

The `.env` file should contain:
```
DATABASE_URL=sqlite:///./mediflow.db
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256
```

2. **Run Database Migrations**

```bash
alembic upgrade head
```

This will create all necessary database tables including:
- users
- facilities
- patients
- patient_identifiers
- referrals
- referral_documents
- voice_notes

### PostgreSQL (Production)

For production deployment, switch to PostgreSQL:

1. **Install PostgreSQL** on your system
2. **Update `.env` file:**
```
DATABASE_URL=postgresql://username:password@localhost:5432/mediflow
```
3. **Update `alembic.ini`:**
```
sqlalchemy.url = postgresql://username:password@localhost:5432/mediflow
```
4. **Run migrations:**
```bash
alembic upgrade head
```

## Initial Super Admin Setup

After running migrations, create the initial super admin user:

```bash
python app/db/seed_initial_admin.py
```

**Default Credentials:**
- Email: `admin@mediflow.com`
- Password: `admin123`

**Important:** Change the default password after first login!

## Running the Backend

### Development Server

Start the FastAPI server with hot reload:

```bash
uvicorn app.main:app --reload
```

The server will run on `http://127.0.0.1:8000`

### API Documentation

Once the server is running, access the interactive API documentation:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Base URL

All API endpoints are prefixed with `/api/v1`:
```
http://127.0.0.1:8000/api/v1
```

## Authentication

The super admin can authenticate using the `/api/v1/auth/login` endpoint:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@mediflow.com", "password": "admin123"}'
```

This will return an access token that can be used in subsequent requests.

## Project Structure

```
mediflow_backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API route handlers
│   │       └── api.py          # API router aggregation
│   ├── core/
│   │   ├── config.py          # Configuration settings
│   │   ├── database.py        # Database session management
│   │   └── security.py        # Authentication utilities
│   ├── db/
│   │   └── seed_initial_admin.py  # Super admin seed script
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic layer
│   └── utils/                 # Utility functions
├── alembic/
│   └── versions/              # Database migration files
├── .env                       # Environment variables
├── alembic.ini                # Alembic configuration
└── requirements.txt           # Python dependencies
```

## Troubleshooting

### Migration Errors

If you encounter migration errors:

1. Check that the database URL in `.env` matches your setup
2. Ensure all dependencies are installed
3. For SQLite, ensure the database file directory is writable

### Port Already in Use

If port 8000 is already in use, specify a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

### Import Errors

If you encounter import errors, ensure:
1. You're in the project root directory
2. The virtual environment is activated
3. All dependencies are installed

## Development Notes

- The backend uses FastAPI with SQLAlchemy ORM
- Alembic is used for database migrations
- JWT tokens are used for authentication
- Role-based access control is implemented
- SQLite is used for development, PostgreSQL for production

## Next Steps

After setup:
1. Change the default super admin password
2. Create facilities using the super admin account
3. Create users for each facility
4. Start creating patients and referrals

## Support

For issues or questions, refer to the API documentation at `/docs` or check the code comments.

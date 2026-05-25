from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets
import warnings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Mediflow Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/mediflow"

    # Security
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]

    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # AI Integration
    OPENAI_API_KEY: Optional[str] = None
    WHISPER_MODEL: str = "large-v3"

    # Groq AI (Llama 3.1 8B) - Primary text AI
    GROQ_API_KEY: Optional[str] = None

    # OCR Configuration
    TESSERACT_PATH: str = ""

    # SMTP Configuration (Google SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "MediFlow"
    SMTP_USE_TLS: bool = True

    # Frontend Configuration
    FRONTEND_URL: str = "https://mediflow-frontend-jor1ipuvr.vercel.app/"

    # Refresh Token Configuration
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Server
    PORT: int = 8000

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError(
                    "SECRET_KEY must be set in production. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                )
            self.SECRET_KEY = secrets.token_urlsafe(64)
            warnings.warn(
                "SECRET_KEY not set — using auto-generated key. "
                "Set SECRET_KEY in .env for persistent sessions.",
                stacklevel=2,
            )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()

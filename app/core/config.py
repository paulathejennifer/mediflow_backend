from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import secrets
import warnings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Mediflow Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost/mediflow"
    )

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    ALGORITHM: str = "HS256"

    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]

    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # AI Integration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")

    # Groq AI (Llama 3.1 8B) - Primary text AI
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")

    # OCR Configuration
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "")

    # SMTP Configuration (Google SMTP)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "MediFlow")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    # Frontend Configuration
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Refresh Token Configuration
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))

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

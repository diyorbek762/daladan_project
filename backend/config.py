"""
Daladan Platform — Configuration
Loads environment variables and provides typed settings via Pydantic.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # ── App ──
    APP_NAME: str = "Daladan Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ── Database ──
    # Example: postgresql+asyncpg://user:pass@host:5432/dbname
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/daladan"

    # ── AI / GenAI ──
    GOOGLE_API_KEY: str = ""

    # ── JWT / Auth ──
    JWT_SECRET_KEY: str = "daladan-super-secret-change-in-production-2026"
    JWT_REFRESH_SECRET_KEY: str = "daladan-refresh-secret-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Encryption (PII) ──
    FERNET_KEY: str = ""  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["*"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton for app settings."""
    return Settings()

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    """Central application settings loaded from environment variables or .env file."""

    APP_NAME: str = "FitBuddy"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    SECRET_KEY: str = "fitbuddy-dev-secret-key-change-in-production-1234567890"

    # Database
    DATABASE_URL: str = "sqlite:///./fitbuddy.db"
    POSTGRES_URL: Optional[str] = None
    POSTGRES_URL_NON_POOLING: Optional[str] = None
    POSTGRES_PRISMA_URL: Optional[str] = None

    # Google Gemini AI Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_WORKOUT_MODEL: str = "gemini-2.5-flash"
    GEMINI_FAST_MODEL: str = "gemini-2.5-flash"

    # Admin Credentials
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "adminpassword123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def resolve_db_url(self) -> "Settings":
        """Resolves the database URL, preferring Vercel/Supabase Postgres for production."""
        pg_url = (
            self.POSTGRES_URL_NON_POOLING
            or os.environ.get("POSTGRES_URL_NON_POOLING")
            or self.POSTGRES_URL
            or os.environ.get("POSTGRES_URL")
        )
        if pg_url:
            url = pg_url
        else:
            url = self.DATABASE_URL or os.environ.get("DATABASE_URL") or "sqlite:///./fitbuddy.db"

        # Fix postgres:// or postgresql:// prefix for SQLAlchemy psycopg2 driver
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

        self.DATABASE_URL = url
        return self


@lru_cache
def get_settings() -> Settings:
    """Returns cached settings instance."""
    return Settings()


"""
Application configuration.

Loads environment variables using Pydantic Settings and exposes a
singleton `settings` object for use across the application.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ======================================================
    # Application
    # ======================================================

    APP_NAME: str = Field(
        default="PDF Backend API",
        description="Application name",
    )

    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version",
    )

    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        """Accept common environment names accidentally supplied as DEBUG."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "off", "no"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "on", "yes"}:
                return True
        return value

    ENVIRONMENT: str = Field(
        default="development",
        description="Running environment",
    )

    # ======================================================
    # Server
    # ======================================================

    HOST: str = Field(
        default="0.0.0.0",
        description="Server host",
    )

    PORT: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server port",
    )

    # ======================================================
    # Storage
    # ======================================================

    STORAGE_DIR: str = Field(
        default="storage",
        description="Storage directory",
    )

    UPLOAD_DIR: str = Field(
        default="storage/uploads",
        description="Upload directory",
    )

    OUTPUT_DIR: str = Field(
        default="storage/outputs",
        description="Processed output directory",
    )

    ANNOTATION_DIR: str = Field(
        default="storage/annotations",
        description="Annotations storage directory",
    )

    TEMP_DIR: str = Field(
        default="temp",
        description="Temporary directory",
    )

    # ======================================================
    # File Limits
    # ======================================================

    MAX_UPLOAD_SIZE_MB: int = Field(
        default=100,
        ge=1,
        description="Maximum upload size in MB",
    )

    MAX_UPLOAD_FILES: int = Field(
        default=20,
        ge=1,
        description="Maximum number of uploaded files",
    )

    # ======================================================
    # Cleanup
    # ======================================================

    FILE_EXPIRY_MINUTES: int = Field(
        default=30,
        ge=1,
        description="Generated files expiry time",
    )

    CLEANUP_INTERVAL_SECONDS: int = Field(
        default=300,
        ge=30,
        description="Cleanup scheduler interval",
    )

    # ======================================================
    # Logging
    # ======================================================

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level",
    )

    # ======================================================
    # CORS
    # ======================================================

    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8002",
            "http://127.0.0.1:8002",
            "https://crod-legal-pdf.vercel.app",
            "https://crod-legal-pdf-git-main-crccf.vercel.app",
        ],
        description="Allowed CORS origins",
    )

    # ======================================================
    # API
    # ======================================================

    API_PREFIX: str = Field(
        default="/api",
        description="Base API prefix",
    )

    # ======================================================
    # Computed compatibility shims for image processing routes
    # ======================================================

    @property
    def MAX_UPLOAD_SIZE(self) -> int:
        """Maximum upload size in bytes (computed from MAX_UPLOAD_SIZE_MB)."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    """
    return Settings()


settings = get_settings()

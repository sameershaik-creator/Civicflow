import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the backend (app/..)
BASE_DIR = Path(__file__).resolve().parent.parent
# Look for .env in current backend dir or project root
ENV_FILE = BASE_DIR / ".env" if (BASE_DIR / ".env").exists() else BASE_DIR.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment Mode ('development', 'staging', 'production')
    ENVIRONMENT: str = "development"

    # Security & Auth
    SECRET_KEY: str = "civicflow-super-secret-key-for-development-purposes-min32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database
    DATABASE_URL: str = "sqlite:///./civicflow.db"

    # AI Provider
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    # Geocoding & Mapping
    GEOCODING_USER_AGENT: str = "CivicFlow/1.0 (civicflow-dev@users.noreply.github.com)"
    GEOCODING_BASE_URL: str = "https://nominatim.openstreetmap.org"
    GEOCODING_TIMEOUT_SECONDS: int = 10
    LOCATION_MISMATCH_THRESHOLD_METERS: float = 500.0

    # Server & Networking
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Media Uploads & Storage
    STORAGE_BACKEND: str = "local"  # 'local', 'supabase', or 's3'
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "complaints"
    STORAGE_BUCKET_NAME: str = ""
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_ACCESS_KEY_ID: str = ""
    STORAGE_SECRET_ACCESS_KEY: str = ""
    STORAGE_PUBLIC_BASE_URL: str = ""
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: Union[str, List[str]] = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip().rstrip("/") for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [i.rstrip("/") if isinstance(i, str) else i for i in v]
        return v

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def assemble_allowed_extensions(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def resolve_database_url(cls, v: str) -> str:
        # Standardize PostgreSQL URLs to use psycopg2 driver explicitly
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+psycopg2://", 1)
        elif v.startswith("postgresql+psycopg://"):
            v = v.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+psycopg2://", 1)

        if v.startswith("sqlite:///./") or v.startswith("sqlite:////./"):
            rel_file = v.replace("sqlite:////./", "").replace("sqlite:///./", "")
            abs_path = (BASE_DIR / rel_file).resolve().as_posix()
            return f"sqlite:///{abs_path}"
        return v


settings = Settings()

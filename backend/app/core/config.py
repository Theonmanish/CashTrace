"""Application configuration and environment settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve path to backend/.env regardless of where uvicorn is launched
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Local development and production settings."""

    model_config = SettingsConfigDict(
        env_file=(str(ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    frontend_origin: str = "http://localhost:3000"

    # Supabase Configuration
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""


settings = Settings()

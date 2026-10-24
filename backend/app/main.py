"""Minimal FastAPI application for CashTrace."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Local development settings loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    frontend_origin: str = "http://localhost:3000"


settings = Settings()

app = FastAPI(title="CashTrace", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "project": "CashTrace",
        "status": "repository foundation ready",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

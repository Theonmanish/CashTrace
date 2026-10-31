"""FastAPI application for CashTrace."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.supabase import get_supabase_admin_client, get_supabase_client

app = FastAPI(title="CashTrace API", version="0.1.0")

# Parse comma-separated origins from FRONTEND_ORIGIN env var
configured_origins = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()]
allowed_origins = list(dict.fromkeys(configured_origins + ["http://localhost:3000", "http://127.0.0.1:3000"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "project": "CashTrace",
        "status": "CashTrace API ready",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/supabase/status")
def supabase_status() -> dict[str, str | bool]:
    """Check if Supabase connection details are configured and reachable."""
    configured = bool(settings.supabase_url and settings.supabase_key)
    if not configured:
        return {
            "configured": False,
            "message": "SUPABASE_URL and SUPABASE_KEY are not configured in backend/.env",
        }

    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        return {
            "configured": False,
            "message": "Failed to initialize Supabase client",
        }

    try:
        # Check connection by querying accounts count (limit 1)
        response = client.table("accounts").select("id").limit(1).execute()
        return {
            "configured": True,
            "connected": True,
            "message": "Successfully connected to Supabase database",
        }
    except Exception as exc:
        return {
            "configured": True,
            "connected": False,
            "error": str(exc),
        }

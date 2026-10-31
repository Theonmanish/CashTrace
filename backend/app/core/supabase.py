"""Supabase client initialization for CashTrace backend."""

from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Return standard client with anon/public key (respects RLS)."""
    global _supabase_client
    if _supabase_client is None and settings.supabase_url and settings.supabase_key:
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


def get_supabase_admin_client() -> Optional[Client]:
    """Return admin client with service role key (bypasses RLS for analysis/system jobs)."""
    global _supabase_admin_client
    key = settings.supabase_service_role_key or settings.supabase_key
    if _supabase_admin_client is None and settings.supabase_url and key:
        _supabase_admin_client = create_client(settings.supabase_url, key)
    return _supabase_admin_client

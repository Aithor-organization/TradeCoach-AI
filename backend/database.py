"""Supabase client singleton"""
import os, logging
from functools import lru_cache
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        logger.warning("SUPABASE_URL/KEY not set, returning None")
        return None
    return create_client(url, key)

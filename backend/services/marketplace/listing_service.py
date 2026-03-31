"""Strategy listing CRUD with filters, sorting, pagination"""
import logging
from typing import List
logger = logging.getLogger(__name__)

class ListingService:
    def __init__(self, db=None): self._db=db
    async def list_listings(self, category=None, verified_only=False, sort_by="created_at", limit=20, offset=0, **filters):
        q = self._db.table("strategy_listings").select("*").eq("is_active", True) if self._db else None
        if not q: return []
        if category: q = q.eq("category", category)
        if verified_only: q = q.eq("is_verified", True)
        q = q.order(sort_by, desc=True).range(offset, offset+limit-1)
        return (q.execute()).data or []
    async def create_listing(self, **data):
        if not self._db: raise RuntimeError("DB not available")
        return (self._db.table("strategy_listings").insert(data).execute()).data[0]
    async def get_listing(self, listing_id):
        if not self._db: return None
        resp = self._db.table("strategy_listings").select("*").eq("id", listing_id).single().execute()
        return resp.data

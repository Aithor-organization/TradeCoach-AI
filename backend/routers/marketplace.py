"""Marketplace API: 9 endpoints for listings, purchase, rent, licenses, rankings, revenue"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/marketplace", tags=["marketplace"])

class PurchaseReq(BaseModel): buyer_wallet: str; tx_signature: str=""
class RentReq(BaseModel): renter_wallet: str; days: int=Field(ge=1,le=365); tx_signature: str=""
class ListingReq(BaseModel): strategy_id: str; name: str; description: str=""; category: str="general"; price: float=Field(gt=0); rental_daily: Optional[float]=None; owner_wallet: str

def _get_db():
    from database import get_supabase
    return get_supabase()

@router.get("/strategies")
async def list_strategies(category: Optional[str]=None, verified: bool=False, sort: str="created_at", limit: int=Query(20,ge=1,le=100), offset: int=Query(0,ge=0)):
    from services.marketplace import ListingService
    return await ListingService(_get_db()).list_listings(category=category, verified_only=verified, sort_by=sort, limit=limit, offset=offset)

@router.post("/strategies", status_code=201)
async def create_strategy(body: ListingReq):
    from services.marketplace import ListingService
    return await ListingService(_get_db()).create_listing(**body.model_dump())

@router.get("/strategies/{id}")
async def get_strategy(id: str):
    from services.marketplace import ListingService
    r = await ListingService(_get_db()).get_listing(id)
    if not r: raise HTTPException(404, "Not found")
    return r

@router.post("/strategies/{id}/purchase", status_code=201)
async def purchase(id: str, body: PurchaseReq):
    from services.marketplace import PurchaseService
    listing = await ListingService(_get_db()).get_listing(id)
    if not listing: raise HTTPException(404)
    return await PurchaseService(_get_db()).execute_purchase(id, body.buyer_wallet, listing.get("price_usdc",0), body.tx_signature)

@router.post("/strategies/{id}/rent", status_code=201)
async def rent(id: str, body: RentReq):
    from services.marketplace import EscrowService, ListingService
    listing = await ListingService(_get_db()).get_listing(id)
    if not listing: raise HTTPException(404)
    return await EscrowService(_get_db()).create_escrow(id, body.renter_wallet, listing.get("creator_address",""), body.days, listing.get("rental_price_per_day",0))

@router.get("/licenses")
async def my_licenses(wallet: str=Query(..., min_length=32)):
    db=_get_db()
    if not db: return []
    return (db.table("licenses").select("*").eq("holder_address",wallet).eq("status","active").execute()).data or []

@router.get("/rankings")
async def rankings(category: str="overall", limit: int=Query(20,ge=1,le=100)):
    from services.marketplace import RankingService
    return await RankingService(_get_db()).get_rankings(category, limit)

@router.get("/revenue/{wallet}")
async def revenue(wallet: str):
    db=_get_db()
    if not db: return {"total":0,"unclaimed":0}
    records = (db.table("revenue_records").select("*").eq("creator_address",wallet).execute()).data or []
    total=sum(r.get("creator_amount_usdc",0) for r in records)
    unclaimed=sum(r.get("creator_amount_usdc",0) for r in records if not r.get("claimed"))
    return {"total":round(total,6),"unclaimed":round(unclaimed,6),"records":records}

@router.post("/revenue/{wallet}/claim")
async def claim(wallet: str):
    db=_get_db()
    if not db: raise HTTPException(500,"DB not available")
    db.table("revenue_records").update({"claimed":True}).eq("creator_address",wallet).eq("claimed",False).execute()
    return {"success":True,"message":"Revenue claimed"}

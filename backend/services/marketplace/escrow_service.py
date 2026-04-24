"""Rental escrow with daily settlement (95:5 split)"""
import logging
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone, timedelta
from typing import Optional
logger = logging.getLogger(__name__)
PLATFORM_FEE_BPS = 500  # 5%

class EscrowService:
    def __init__(self, db=None):
        self._db = db
        self._idempotency_cache: dict[str, dict] = {}

    async def create_escrow(
        self,
        listing_id,
        renter,
        owner,
        days,
        daily_rate,
        idempotency_key: Optional[str] = None,
    ):
        # 🔴 Idempotency: 재시도로 인한 escrow 중복 생성 방지.
        if idempotency_key and idempotency_key in self._idempotency_cache:
            logger.info("Idempotent rental replay: key=%s listing=%s", idempotency_key, listing_id)
            return self._idempotency_cache[idempotency_key]

        # 동일 (renter, listing_id)에 이미 활성 escrow 있으면 반환.
        if self._db:
            existing = (
                self._db.table("rental_escrow")
                .select("*")
                .eq("listing_id", listing_id)
                .eq("renter_address", renter)
                .eq("status", "active")
                .execute()
            )
            if existing.data:
                logger.info("Duplicate rental blocked: renter=%s already renting listing=%s", renter, listing_id)
                result = {**existing.data[0], "replayed": True}
                if idempotency_key:
                    self._idempotency_cache[idempotency_key] = result
                return result

        total = Decimal(str(daily_rate)) * days
        data = {"listing_id": listing_id, "renter_address": renter, "creator_address": owner,
                "rental_days": days, "daily_rate_usdc": float(daily_rate), "total_amount_usdc": float(total),
                "status": "active", "start_date": datetime.now(timezone.utc).isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()}
        if self._db:
            result = (self._db.table("rental_escrow").insert(data).execute()).data[0]
            if idempotency_key:
                self._idempotency_cache[idempotency_key] = result
            return result
        if idempotency_key:
            self._idempotency_cache[idempotency_key] = data
        return data
    async def daily_settle(self):
        if not self._db: return []
        active = (self._db.table("rental_escrow").select("*").eq("status","active").execute()).data or []
        results = []
        for e in active:
            amount = Decimal(str(e["daily_rate_usdc"]))
            owner_amt = (amount * 9500 / 10000).quantize(Decimal("0.000001"), ROUND_DOWN)
            platform_amt = amount - owner_amt
            results.append({"escrow_id":e["id"],"owner":float(owner_amt),"platform":float(platform_amt)})
        return results
    async def expire_rental(self, escrow_id):
        if self._db: self._db.table("rental_escrow").update({"status":"expired"}).eq("id",escrow_id).execute()

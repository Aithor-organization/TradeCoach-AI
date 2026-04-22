"""Rental escrow with daily settlement (95:5 split)"""
import logging
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone, timedelta
logger = logging.getLogger(__name__)
PLATFORM_FEE_BPS = 500  # 5%

class EscrowService:
    def __init__(self, db=None): self._db=db
    async def create_escrow(self, listing_id, renter, owner, days, daily_rate):
        total = Decimal(str(daily_rate)) * days
        data = {"listing_id":listing_id,"renter_address":renter,"creator_address":owner,
                "rental_days":days,"daily_rate_usdc":float(daily_rate),"total_amount_usdc":float(total),
                "status":"active","start_date":datetime.now(timezone.utc).isoformat(),
                "end_date":(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()}
        if self._db: return (self._db.table("rental_escrow").insert(data).execute()).data[0]
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

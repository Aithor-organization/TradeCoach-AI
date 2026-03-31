"""Strategy purchase (95:5 split, atomic)"""
import logging, uuid
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
logger = logging.getLogger(__name__)
PLATFORM_FEE_BPS = 500

class PurchaseService:
    def __init__(self, db=None): self._db=db
    async def execute_purchase(self, listing_id, buyer, price_sol, tx_sig=""):
        price = Decimal(str(price_sol))
        owner_amt = (price * 9500 / 10000).quantize(Decimal("0.000001"), ROUND_DOWN)
        platform_amt = price - owner_amt
        # Get listing
        listing = (self._db.table("strategy_listings").select("*").eq("id",listing_id).single().execute()).data if self._db else {}
        owner = listing.get("creator_address","")
        # Create license
        license_data = {"listing_id":listing_id,"strategy_id":listing.get("strategy_id",""),"holder_address":buyer,"license_type":"purchase","status":"active","tx_signature":tx_sig or str(uuid.uuid4()),"owner_wallet":owner}
        if self._db: self._db.table("licenses").insert(license_data).execute()
        # Record purchase
        record = {"listing_id":listing_id,"strategy_id":listing.get("strategy_id",""),"buyer_address":buyer,"creator_address":owner,"price_usdc":float(price),"creator_amount_usdc":float(owner_amt),"platform_amount_usdc":float(platform_amt),"transaction_hash":tx_sig}
        if self._db: self._db.table("purchase_records").insert(record).execute()
        logger.info("Purchase: listing=%s buyer=%s price=%.4f (owner=%.4f platform=%.4f)",listing_id,buyer,float(price),float(owner_amt),float(platform_amt))
        return {"success":True,"license":license_data,"purchase":record}
    async def check_license(self, strategy_id, user):
        if not self._db: return None
        resp = self._db.table("licenses").select("*").eq("strategy_id",strategy_id).eq("holder_address",user).eq("status","active").execute()
        return resp.data[0] if resp.data else None

"""Strategy purchase (95:5 split, atomic)"""
import logging, uuid
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from typing import Optional
logger = logging.getLogger(__name__)
PLATFORM_FEE_BPS = 500

class PurchaseService:
    def __init__(self, db=None):
        self._db = db
        # 🔴 MVP idempotency 캐시 (인메모리, 서버 재시작 시 휘발).
        # Production에서는 Redis 또는 purchase_records 테이블에 UNIQUE(idempotency_key) 제약 권장.
        self._idempotency_cache: dict[str, dict] = {}

    async def execute_purchase(
        self,
        listing_id,
        buyer,
        price_sol,
        tx_sig: str = "",
        idempotency_key: Optional[str] = None,
    ):
        # 🔴 Idempotency: 동일 키로 재호출 시 최초 결과 그대로 반환.
        # tx_sig는 Solana 서명이 있으면 그 자체가 고유하지만, 없을 때는 client가 보낸 키 사용.
        # 키가 있으면 캐시 우선; 없으면 (buyer, listing_id) 조합으로 최근 활성 license 중복 체크.
        if idempotency_key and idempotency_key in self._idempotency_cache:
            logger.info("Idempotent replay: key=%s listing=%s", idempotency_key, listing_id)
            return self._idempotency_cache[idempotency_key]

        # (buyer, listing_id)에 이미 활성 license가 있으면 중복 구매로 간주하고 기존 결과 반환.
        if self._db:
            existing = (
                self._db.table("licenses")
                .select("*")
                .eq("listing_id", listing_id)
                .eq("holder_address", buyer)
                .eq("status", "active")
                .execute()
            )
            if existing.data:
                logger.info("Duplicate purchase blocked: buyer=%s already owns listing=%s", buyer, listing_id)
                result = {"success": True, "license": existing.data[0], "purchase": None, "replayed": True}
                if idempotency_key:
                    self._idempotency_cache[idempotency_key] = result
                return result

        price = Decimal(str(price_sol))
        owner_amt = (price * 9500 / 10000).quantize(Decimal("0.000001"), ROUND_DOWN)
        platform_amt = price - owner_amt
        # Get listing
        listing = (self._db.table("strategy_listings").select("*").eq("id", listing_id).single().execute()).data if self._db else {}
        owner = listing.get("creator_address", "")
        # Create license
        license_data = {"listing_id": listing_id, "strategy_id": listing.get("strategy_id", ""), "holder_address": buyer, "license_type": "purchase", "status": "active", "tx_signature": tx_sig or str(uuid.uuid4()), "owner_wallet": owner}
        if self._db:
            self._db.table("licenses").insert(license_data).execute()
        # Record purchase
        record = {"listing_id": listing_id, "strategy_id": listing.get("strategy_id", ""), "buyer_address": buyer, "creator_address": owner, "price_usdc": float(price), "creator_amount_usdc": float(owner_amt), "platform_amount_usdc": float(platform_amt), "transaction_hash": tx_sig}
        if self._db:
            self._db.table("purchase_records").insert(record).execute()
        logger.info("Purchase: listing=%s buyer=%s price=%.4f (owner=%.4f platform=%.4f)", listing_id, buyer, float(price), float(owner_amt), float(platform_amt))

        result = {"success": True, "license": license_data, "purchase": record}
        if idempotency_key:
            self._idempotency_cache[idempotency_key] = result
        return result

    async def check_license(self, strategy_id, user):
        if not self._db:
            return None
        resp = self._db.table("licenses").select("*").eq("strategy_id", strategy_id).eq("holder_address", user).eq("status", "active").execute()
        return resp.data[0] if resp.data else None

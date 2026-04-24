import logging
from fastapi import APIRouter, HTTPException

from services.price_feed import get_token_price, get_all_prices

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/prices")
async def get_prices():
    """주요 토큰 실시간 가격 일괄 조회 (CoinGecko Simple Price API)"""
    try:
        prices = await get_all_prices()
        return {"prices": prices}
    except Exception as e:
        logger.error(f"토큰 가격 일괄 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="가격 정보를 불러올 수 없습니다.")


@router.get("/price/{symbol}")
async def get_price(symbol: str):
    """단일 토큰 가격 조회"""
    try:
        price = await get_token_price(symbol.upper())
        if price is None:
            raise HTTPException(status_code=404, detail=f"Token '{symbol}' not found")
        return {"symbol": symbol.upper(), "price": price}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 가격 조회 실패 (symbol={symbol}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="가격 정보를 불러올 수 없습니다.")

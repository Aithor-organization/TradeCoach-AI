"""
Phase 3: 모의투자 API 엔드포인트.

POST /trading/demo/start  — 모의투자 세션 시작
POST /trading/demo/stop   — 모의투자 세션 종료
GET  /trading/demo/status  — 현재 포지션/잔고/PnL
GET  /trading/demo/history — 거래 내역
"""

import asyncio
import logging
import uuid
from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re
from dependencies import get_current_user_id
from routers.auth import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

# 인메모리 세션 저장소 (프로덕션에서는 Redis/DB 사용)
_active_sessions: dict = {}


class DemoStartRequest(BaseModel):
    strategy_id: Optional[str] = None
    parsed_strategy: Optional[dict] = None
    symbol: str = Field(default="BTCUSDT", max_length=20)
    leverage: int = Field(default=10, ge=1, le=125, description="레버리지 (1-125x)")
    initial_balance: float = Field(default=1000.0, gt=0, description="초기 잔고 (0보다 커야 함)")
    strategy_nft_id: Optional[str] = None  # Phase 5: 신호 기록용 NFT ID

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9]{1,20}$", v):
            raise ValueError("symbol은 영문/숫자만 허용 (최대 20자)")
        return v.upper()


class DemoStopRequest(BaseModel):
    session_id: str
    record_mode: str = "test"  # "test" = DB만, "verify" = 블록체인 기록


@router.post("/demo/start")
@limiter.limit("5/minute")
async def start_demo(
    request: Request,
    body: DemoStartRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """모의투자 세션 시작"""
    from services.demo_trading import DemoSession, DemoEngine

    session_id = str(uuid.uuid4())
    session = DemoSession(
        session_id=session_id,
        symbol=body.symbol,
        leverage=body.leverage,
        initial_balance=body.initial_balance,
        current_balance=body.initial_balance,
    )

    strategy_config = body.parsed_strategy or {}
    engine = DemoEngine(session=session, strategy_config=strategy_config)
    _active_sessions[session_id] = {
        "engine": engine,
        "user_id": user_id,
        "last_signal": None,
        "strategy_nft_id": body.strategy_nft_id or body.strategy_id or session_id,
    }

    # 백그라운드 가격 피드 + 자동 신호 평가 시작
    from services.demo_price_feed import run_price_feed
    task = asyncio.create_task(
        run_price_feed(session_id, engine, strategy_config, _active_sessions)
    )
    _active_sessions[session_id]["feed_task"] = task

    logger.info(f"모의투자 시작: {session_id}, {body.symbol} {body.leverage}x, 전략: {bool(strategy_config)}")
    return {
        "session_id": session_id,
        "symbol": body.symbol,
        "leverage": body.leverage,
        "initial_balance": body.initial_balance,
        "status": "active",
    }


@router.post("/demo/stop")
async def stop_demo(
    body: DemoStopRequest,
    user_id: str | None = Depends(get_current_user_id),
):
    """모의투자 세션 종료 + 매매 신호 온체인 기록 (Phase 5)"""
    entry = _active_sessions.pop(body.session_id, None)
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = entry["engine"]
    engine.session.status = "stopped"

    # 백그라운드 가격 피드 중지
    feed_task = entry.get("feed_task")
    if feed_task and not feed_task.done():
        feed_task.cancel()

    # Phase 5: 거래 기록 — record_mode에 따라 분기
    signal_results = []
    strategy_nft_id = entry.get("strategy_nft_id", body.session_id)
    is_verify_mode = body.record_mode == "verify"

    if is_verify_mode:
        # 검증 모드: 블록체인에 기록
        try:
            from services.blockchain.signal_recorder import record_signal, flush_signals_to_chain

            for trade in engine.session.trades:
                # 4종 신호 → signal_recorder 타입 매핑
                sr_entry_type = "long_entry" if trade.side == "long" else "short_entry"
                entry_result = await record_signal(
                    strategy_nft_id=strategy_nft_id,
                    signal_type=sr_entry_type,
                    symbol=engine.session.symbol,
                    price=trade.entry_price,
                    leverage=trade.leverage,
                    timestamp=0,
                )
                signal_results.append(entry_result)

                exit_result = await record_signal(
                    strategy_nft_id=strategy_nft_id,
                    signal_type="close",
                    symbol=engine.session.symbol,
                    price=trade.exit_price,
                    leverage=trade.leverage,
                    timestamp=0,
                )
                signal_results.append(exit_result)

            flush_result = await flush_signals_to_chain(
                session_id=body.session_id,
                strategy_id=strategy_nft_id,
            )
            logger.info(
                f"검증 모드 — 온체인 기록: {flush_result.get('flushed', 0)}개 플러시, "
                f"tx={flush_result.get('tx_signature', 'N/A')}"
            )
        except Exception as e:
            logger.warning(f"신호 기록 실패 (비치명적): {e}")
            flush_result = {"flushed": 0, "error": str(e)}
    else:
        # 테스트 모드: DB에만 기록 (블록체인 비용 절약)
        logger.info(f"테스트 모드 — 블록체인 기록 스킵, trades={len(engine.session.trades)}")
        flush_result = {"flushed": 0, "mode": "test", "network": "none"}

    # 성과 데이터 업데이트
    performance = None
    try:
        from services.blockchain.strategy_registry_client import update_performance
        session_result = {
            "trades": [{"pnl": t.pnl, "side": t.side, "exit_reason": t.exit_reason} for t in engine.session.trades],
            "signal_recording": {
                "tx_signature": flush_result.get("tx_signature"),
            },
        }
        performance = update_performance(strategy_nft_id, session_result)
    except Exception as e:
        logger.warning(f"성과 업데이트 실패 (비치명적): {e}")

    # 세션 결과 + 개별 거래를 DB에 영속화
    trades_data = [
        {"side": t.side, "signal_type": t.signal_type,
         "entry_price": t.entry_price, "exit_price": t.exit_price,
         "pnl": round(t.pnl, 2), "pnl_pct": round(t.pnl_pct, 2),
         "fee": round(t.fee, 4), "exit_reason": t.exit_reason}
        for t in engine.session.trades
    ]
    try:
        from services.supabase_client import save_trade_session, save_trade_records
        winning = sum(1 for t in engine.session.trades if t.pnl > 0)
        total_pnl = sum(t.pnl for t in engine.session.trades)
        wr = (winning / len(engine.session.trades) * 100) if engine.session.trades else 0
        await save_trade_session(
            strategy_id=strategy_nft_id, session_id=body.session_id,
            record_mode=body.record_mode, symbol=engine.session.symbol,
            leverage=engine.session.leverage, initial_balance=engine.session.initial_balance,
            final_balance=engine.session.current_balance,
            total_trades=len(engine.session.trades), winning_trades=winning,
            total_pnl=total_pnl, win_rate=wr,
            tx_signature=flush_result.get("tx_signature", ""),
        )
        await save_trade_records(strategy_nft_id, body.session_id, trades_data)
    except Exception as e:
        logger.warning(f"세션/거래 DB 저장 실패 (비치명적): {e}")

    # 하이브리드: TX를 DB에도 저장 (서버 재시작 후에도 즉시 조회)
    if is_verify_mode and flush_result.get("tx_signature"):
        try:
            from services.supabase_client import save_trade_tx
            await save_trade_tx(
                strategy_id=strategy_nft_id,
                session_id=body.session_id,
                tx_signature=flush_result["tx_signature"],
                merkle_root=flush_result.get("merkle_root", ""),
                trade_hash=flush_result.get("trade_hash", ""),
                trades_count=len(engine.session.trades),
                network=flush_result.get("network", "devnet"),
                explorer_url=flush_result.get("explorer_url", ""),
                record_mode="verify",
            )
        except Exception as e:
            logger.warning(f"TX DB 저장 실패 (비치명적): {e}")

    return {
        "session_id": body.session_id,
        "status": "stopped",
        "final_balance": engine.session.current_balance,
        "total_trades": len(engine.session.trades),
        "trades": [
            {
                "side": t.side,
                "signal_type": t.signal_type,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": round(t.pnl, 2),
                "pnl_pct": round(t.pnl_pct, 2),
                "fee": round(t.fee, 4),
                "exit_reason": t.exit_reason,
            }
            for t in engine.session.trades
        ],
        "signal_recording": {
            "signals_recorded": len(signal_results),
            "flushed": flush_result.get("flushed", 0),
            "merkle_root": flush_result.get("merkle_root"),
            "network": flush_result.get("network", "devnet"),
            "tx_signature": flush_result.get("tx_signature"),
            "explorer_url": flush_result.get("explorer_url"),
            "trade_hash": flush_result.get("trade_hash"),
        },
        "performance": performance,
        "record_mode": body.record_mode,
    }


@router.get("/demo/status")
async def demo_status(
    session_id: str,
    current_price: Optional[float] = None,
    user_id: str | None = Depends(get_current_user_id),
):
    """현재 포지션/잔고/PnL 조회"""
    entry = _active_sessions.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = entry["engine"]
    status = engine.get_status(current_price)
    # 마지막 신호 정보 추가 (4종 → 프론트 호환 매핑)
    pos = engine.session.position
    if pos:
        status["last_signal"] = pos.side  # "long" or "short"
    elif engine._pending_signal:
        status["last_signal"] = engine._pending_signal  # 4종 신호
    else:
        status["last_signal"] = "wait"
    # 거래 기록 포함
    status["trades"] = [
        {
            "side": t.side,
            "signal_type": t.signal_type,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl": round(t.pnl, 2),
            "pnl_pct": round(t.pnl_pct, 2),
            "fee": round(t.fee, 4),
            "exit_reason": t.exit_reason,
            "entry_at": t.entry_at,
            "exit_at": t.exit_at,
        }
        for t in engine.session.trades
    ]
    return status


@router.get("/demo/history")
async def demo_history(
    session_id: str,
    user_id: str | None = Depends(get_current_user_id),
):
    """거래 내역 조회"""
    entry = _active_sessions.get(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "trades": [
            {
                "side": t.side,
                "signal_type": t.signal_type,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "leverage": t.leverage,
                "pnl": round(t.pnl, 2),
                "pnl_pct": round(t.pnl_pct, 2),
                "fee": round(t.fee, 4),
                "exit_reason": t.exit_reason,
                "entry_at": t.entry_at,
                "exit_at": t.exit_at,
            }
            for t in entry["engine"].session.trades
        ],
    }


@router.websocket("/ws/price/{symbol}")
async def price_stream(websocket: WebSocket, symbol: str):
    """실시간 가격 WebSocket 스트리밍"""
    await websocket.accept()
    try:
        from services.binance_ws import BinanceWSClient

        async def on_bar(bar: dict):
            await websocket.send_json(bar)

        client = BinanceWSClient(
            symbol=symbol.lower(),
            intervals=["1m", "3m", "15m"],
            on_bar=on_bar,
        )
        await client.connect()
    except Exception as e:
        logger.error(f"WebSocket 에러: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

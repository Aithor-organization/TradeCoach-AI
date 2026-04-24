import logging
import httpx
from config import get_settings
from typing import Optional
from data.example_strategies import get_example_strategies, get_example_strategy_by_id

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Shared AsyncClient (연결 재사용으로 커넥션 오버헤드 제거) ────────────────
_shared_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """모듈 수준 공유 AsyncClient 반환. 닫혀 있으면 재생성."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(timeout=10.0)
    return _shared_client

_base_url = settings.supabase_url
_api_key = settings.supabase_service_key
_init_failed = False


def _headers() -> dict:
    return {
        "apikey": _api_key,
        "Authorization": f"Bearer {_api_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _rest_url(table: str) -> str:
    return f"{_base_url}/rest/v1/{table}"


def _is_available() -> bool:
    global _init_failed
    if _init_failed:
        return False
    if not _base_url or not _api_key:
        _init_failed = True
        logger.warning("Supabase 설정 없음 (MVP 모드로 계속)")
        return False
    return True


async def save_nonce(wallet_address: str, nonce: str) -> bool:
    """Nonce를 Supabase에 저장 (upsert)"""
    if not _is_available():
        return False
    try:
        client = _get_client()
        headers = _headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        res = await client.post(
            _rest_url("nonces"),
            headers=headers,
            json={"wallet_address": wallet_address, "nonce": nonce},
        )
        return res.status_code in (200, 201)
    except Exception as e:
        logger.warning(f"save_nonce 실패: {e}")
        return False


async def get_nonce(wallet_address: str) -> Optional[str]:
    """저장된 Nonce 조회"""
    if not _is_available():
        return None
    try:
        client = _get_client()
        res = await client.get(
            _rest_url("nonces"),
            headers=_headers(),
            params={"wallet_address": f"eq.{wallet_address}", "select": "nonce"},
        )
        if res.status_code == 200 and res.json():
            return res.json()[0]["nonce"]
        return None
    except Exception as e:
        logger.warning(f"get_nonce 실패: {e}")
        return None


async def delete_nonce(wallet_address: str) -> bool:
    """사용된 Nonce 삭제"""
    if not _is_available():
        return False
    try:
        client = _get_client()
        res = await client.delete(
            _rest_url("nonces"),
            headers=_headers(),
            params={"wallet_address": f"eq.{wallet_address}"},
        )
        return res.status_code in (200, 204)
    except Exception as e:
        logger.warning(f"delete_nonce 실패: {e}")
        return False


async def get_or_create_user(wallet_address: str) -> Optional[dict]:
    if not _is_available():
        from datetime import datetime, timezone
        return {"id": "local-user", "wallet_address": wallet_address, "tier": "free", "created_at": datetime.now(timezone.utc).isoformat()}
    client = _get_client()
    # 조회
    res = await client.get(
        _rest_url("users"),
        headers=_headers(),
        params={"wallet_address": f"eq.{wallet_address}", "select": "*"},
    )
    if res.status_code == 200 and res.json():
        return res.json()[0]
    # 생성
    res = await client.post(
        _rest_url("users"),
        headers=_headers(),
        json={"wallet_address": wallet_address, "tier": "free"},
    )
    if res.status_code in (200, 201) and res.json():
        return res.json()[0]
    return None


async def get_or_create_user_by_email(
    email: str,
    name: str,
    password_hash: Optional[str] = None,
    fail_if_exists: bool = False,
) -> Optional[dict]:
    """이메일로 사용자 조회 또는 생성 (MVP 간편 가입).

    Args:
        fail_if_exists: True면 기존 유저 발견 시 None 반환 (회원가입 플로우용).
            False(기본)면 기존 유저를 그대로 반환 (기존 호환성 유지).

    ⚠️ SECURITY: 회원가입 시에는 반드시 fail_if_exists=True로 호출할 것.
       그렇지 않으면 공격자가 타인의 이메일로 register를 호출해 JWT를 발급받을 수 있음.
    """
    if not _is_available():
        import uuid
        from datetime import datetime, timezone
        return {"id": str(uuid.uuid4()), "wallet_address": email, "display_name": name, "tier": "free", "created_at": datetime.now(timezone.utc).isoformat()}
    client = _get_client()
    # 이메일로 기존 사용자 조회 (wallet_address 필드를 이메일로 활용)
    res = await client.get(
        _rest_url("users"),
        headers=_headers(),
        params={"wallet_address": f"eq.{email}", "select": "*"},
    )
    if res.status_code == 200 and res.json():
        if fail_if_exists:
            logger.info(f"중복 가입 시도 차단: {email}")
            return None
        return res.json()[0]
    # 신규 생성 — password_hash를 초기 INSERT에 포함 (별도 PATCH 불필요)
    insert_data: dict = {"wallet_address": email, "tier": "free"}
    if password_hash:
        insert_data["password_hash"] = password_hash
    res = await client.post(
        _rest_url("users"),
        headers=_headers(),
        json=insert_data,
    )
    # password_hash 컬럼이 없어서 INSERT 실패한 경우 → 컬럼 없이 재시도
    if res.status_code not in (200, 201) and password_hash:
        logger.warning(f"password_hash 포함 INSERT 실패 ({res.status_code}), 컬럼 없이 재시도")
        insert_data = {"wallet_address": email, "tier": "free"}
        res = await client.post(
            _rest_url("users"),
            headers=_headers(),
            json=insert_data,
        )
    if res.status_code in (200, 201) and res.json():
        data = res.json()
        user = data[0] if isinstance(data, list) else data
        # display_name 업데이트 시도 (컬럼 없으면 무시)
        try:
            await client.patch(
                _rest_url("users"),
                headers=_headers(),
                params={"id": f"eq.{user['id']}"},
                json={"display_name": name},
            )
        except Exception:
            pass
        # password_hash가 INSERT에 포함되지 않았으면 별도 PATCH 시도
        if password_hash and "password_hash" not in insert_data:
            try:
                await client.patch(
                    _rest_url("users"),
                    headers=_headers(),
                    params={"id": f"eq.{user['id']}"},
                    json={"password_hash": password_hash},
                )
            except Exception:
                logger.warning("password_hash PATCH 실패 — Supabase에 컬럼 추가 필요")
        user["display_name"] = name
        return user
    logger.warning(f"Supabase user creation failed: {res.status_code} {res.text}")
    return None


async def get_strategies(user_id: Optional[str] = None) -> list:
    if not _is_available():
        return get_example_strategies()
    if not user_id:
        return []
    try:
        client = _get_client()
        params: dict = {
            "select": "id,name,status,created_at,input_type,parsed_strategy,mint_tx,mint_hash,mint_network,user_id",
            "order": "created_at.desc",
            "limit": "50",
            "user_id": f"eq.{user_id}",
        }
        res = await client.get(
            _rest_url("strategies"),
            headers=_headers(),
            params=params,
        )
        if res.status_code == 200:
            return res.json()
        logger.error(f"get_strategies 실패: {res.status_code} {res.text}")
        return []
    except Exception as e:
        logger.warning(f"get_strategies DB 연결 실패: {e}")
        return get_example_strategies()


async def get_strategy_by_id(strategy_id: str) -> Optional[dict]:
    # 예시 전략은 DB 조회 없이 바로 반환
    example = get_example_strategy_by_id(strategy_id)
    if example:
        return example
    if not _is_available():
        return None
    try:
        client = _get_client()
        res = await client.get(
            _rest_url("strategies"),
            headers=_headers(),
            params={"id": f"eq.{strategy_id}", "select": "*"},
        )
        if res.status_code == 200 and res.json():
            return res.json()[0]
        return None
    except Exception as e:
        logger.warning(f"get_strategy_by_id DB 연결 실패: {e}")
        return None


async def save_strategy(user_id: Optional[str], name: str, raw_input: str,
                        input_type: str, parsed_strategy: dict,
                        image_url: Optional[str] = None) -> dict:
    if not _is_available():
        return {"id": "local-strategy", "name": name, "parsed_strategy": parsed_strategy}
    data = {
        "name": name,
        "raw_input": raw_input,
        "input_type": input_type,
        "parsed_strategy": parsed_strategy,
        "status": "draft",
    }
    if user_id:
        data["user_id"] = user_id
    if image_url:
        data["image_url"] = image_url
    client = _get_client()
    res = await client.post(
        _rest_url("strategies"),
        headers=_headers(),
        json=data,
    )
    if res.status_code in (200, 201) and res.json():
        return res.json()[0]
    logger.error(f"save_strategy 실패: {res.status_code} {res.text}")
    return {"id": "local-strategy", "name": name, "parsed_strategy": parsed_strategy}


async def update_strategy_by_id(strategy_id: str, updates: dict) -> Optional[dict]:
    if not _is_available():
        return None
    client = _get_client()
    res = await client.patch(
        _rest_url("strategies"),
        headers=_headers(),
        params={"id": f"eq.{strategy_id}"},
        json=updates,
    )
    if res.status_code == 200 and res.json():
        return res.json()[0]
    return None


async def delete_strategy_by_id(strategy_id: str) -> bool:
    if not _is_available():
        return False
    client = _get_client()
    res = await client.delete(
        _rest_url("strategies"),
        headers=_headers(),
        params={"id": f"eq.{strategy_id}"},
    )
    return res.status_code == 200


async def save_trade_tx(
    strategy_id: str,
    session_id: str,
    tx_signature: str,
    merkle_root: str = "",
    trade_hash: str = "",
    trades_count: int = 0,
    network: str = "devnet",
    explorer_url: str = "",
    record_mode: str = "verify",
) -> Optional[dict]:
    """TX 기록을 DB에 저장 (하이브리드: 즉시 조회용 캐시)"""
    if not _is_available():
        return None
    try:
        client = _get_client()
        res = await client.post(
            _rest_url("trade_tx_records"),
            headers=_headers(),
            json={
                "strategy_id": strategy_id,
                "session_id": session_id,
                "tx_signature": tx_signature,
                "merkle_root": merkle_root,
                "trade_hash": trade_hash,
                "trades_count": trades_count,
                "network": network,
                "explorer_url": explorer_url,
                "record_mode": record_mode,
            },
        )
        if res.status_code in (200, 201) and res.json():
            return res.json()[0] if isinstance(res.json(), list) else res.json()
        logger.warning(f"save_trade_tx 실패: {res.status_code} {res.text[:100]}")
        return None
    except Exception as e:
        logger.warning(f"save_trade_tx 예외: {e}")
        return None


async def get_trade_tx_records(strategy_id: str, limit: int = 20) -> list:
    """전략의 TX 기록을 DB에서 조회 (즉시, 서버 재시작 무관)"""
    if not _is_available():
        return []
    try:
        client = _get_client()
        res = await client.get(
            _rest_url("trade_tx_records"),
            headers=_headers(),
            params={
                "strategy_id": f"eq.{strategy_id}",
                "select": "id,strategy_id,tx_signature,merkle_root,network,explorer_url,created_at",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        return res.json() if res.status_code == 200 else []
    except Exception as e:
        logger.warning(f"get_trade_tx_records 예외: {e}")
        return []


async def save_trade_session(
    strategy_id: str, session_id: str, record_mode: str,
    symbol: str, leverage: int, initial_balance: float, final_balance: float,
    total_trades: int, winning_trades: int, total_pnl: float, win_rate: float,
    tx_signature: str = "",
) -> Optional[dict]:
    """트레이딩 세션 결과를 DB에 저장"""
    if not _is_available():
        return None
    try:
        client = _get_client()
        res = await client.post(
            _rest_url("trade_sessions"),
            headers=_headers(),
            json={
                "strategy_id": strategy_id, "session_id": session_id,
                "record_mode": record_mode, "symbol": symbol,
                "leverage": leverage, "initial_balance": initial_balance,
                "final_balance": final_balance, "total_trades": total_trades,
                "winning_trades": winning_trades, "total_pnl": round(total_pnl, 4),
                "win_rate": round(win_rate, 2), "tx_signature": tx_signature,
            },
        )
        if res.status_code in (200, 201):
            data = res.json()
            return data[0] if isinstance(data, list) and data else data
        logger.warning(f"save_trade_session: {res.status_code}")
    except Exception as e:
        logger.warning(f"save_trade_session 예외: {e}")
    return None


async def save_trade_records(strategy_id: str, session_id: str, trades: list[dict]) -> int:
    """개별 거래 기록을 DB에 배치 저장"""
    if not _is_available() or not trades:
        return 0
    try:
        rows = [
            {
                "strategy_id": strategy_id, "session_id": session_id,
                "trade_index": i, "side": t.get("side", ""),
                "entry_price": t.get("entry_price", 0),
                "exit_price": t.get("exit_price", 0),
                "pnl": round(t.get("pnl", 0), 4),
                "exit_reason": t.get("exit_reason", ""),
            }
            for i, t in enumerate(trades)
        ]
        client = _get_client()
        res = await client.post(
            _rest_url("trade_records"),
            headers=_headers(),
            json=rows,
        )
        if res.status_code in (200, 201):
            return len(rows)
        logger.warning(f"save_trade_records: {res.status_code}")
    except Exception as e:
        logger.warning(f"save_trade_records 예외: {e}")
    return 0


async def get_strategy_performance_db(strategy_id: str) -> Optional[dict]:
    """전략의 누적 성과를 DB에서 집계 (equity_curve 포함)"""
    if not _is_available():
        return None
    try:
        client = _get_client()
        res = await client.get(
            _rest_url("trade_sessions"),
            headers=_headers(),
            params={
                "strategy_id": f"eq.{strategy_id}",
                "select": "total_trades,winning_trades,total_pnl,win_rate,tx_signature,created_at",
                "order": "created_at.asc",
                "limit": "50",
            },
        )
        if res.status_code != 200:
            return None
        sessions = res.json()
        if not sessions:
            return None
        total_trades = sum(s.get("total_trades", 0) for s in sessions)
        winning = sum(s.get("winning_trades", 0) for s in sessions)
        total_pnl = sum(float(s.get("total_pnl", 0)) for s in sessions)
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        tx_sigs = [s["tx_signature"] for s in sessions if s.get("tx_signature")]

        # 개별 트레이드 기반 equity curve (trade_records 테이블)
        equity_curve = []
        try:
            tr_res = await client.get(
                _rest_url("trade_records"),
                headers=_headers(),
                params={
                    "strategy_id": f"eq.{strategy_id}",
                    "select": "pnl,created_at",
                    "order": "created_at.asc",
                    "limit": "500",
                },
            )
            if tr_res.status_code == 200 and tr_res.json():
                cumulative = 0.0
                for tr in tr_res.json():
                    cumulative += float(tr.get("pnl", 0))
                    equity_curve.append({"t": tr["created_at"], "v": round(cumulative, 2)})
        except Exception:
            pass
        # trade_records가 없으면 세션 기반 폴백
        if not equity_curve:
            cumulative = 0.0
            for s in sessions:
                cumulative += float(s.get("total_pnl", 0))
                equity_curve.append({"t": s["created_at"], "v": round(cumulative, 2)})

        return {
            "strategy_id": strategy_id,
            "total_trades": total_trades,
            "winning_trades": winning,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "sessions": len(sessions),
            "tx_signatures": tx_sigs[:10],
            "verified": len(tx_sigs) > 0,
            "equity_curve": equity_curve,
        }
    except Exception as e:
        logger.warning(f"get_strategy_performance_db 예외: {e}")
    return None


async def get_batch_strategy_performance_db(strategy_ids: list[str]) -> dict:
    """여러 전략의 성과를 IN 쿼리로 한 번에 조회 (equity_curve 포함)"""
    if not _is_available() or not strategy_ids:
        return {}
    try:
        ids_str = ",".join(str(sid) for sid in strategy_ids)
        client = _get_client()
        res = await client.get(
            _rest_url("trade_sessions"),
            headers=_headers(),
            params={
                "strategy_id": f"in.({ids_str})",
                "select": "strategy_id,total_trades,winning_trades,total_pnl,tx_signature,created_at",
                "order": "created_at.asc",
                "limit": "500",
            },
        )
        if res.status_code != 200:
            return {}
        all_sessions = res.json()

        # strategy_id별 그룹화
        grouped: dict[str, list] = {}
        for s in all_sessions:
            sid = s.get("strategy_id")
            if sid:
                grouped.setdefault(sid, []).append(s)

        # 개별 트레이드 기반 equity curve (trade_records 배치 조회)
        trade_records_grouped: dict[str, list] = {}
        try:
            tr_res = await client.get(
                _rest_url("trade_records"),
                headers=_headers(),
                params={
                    "strategy_id": f"in.({ids_str})",
                    "select": "strategy_id,pnl,created_at",
                    "order": "created_at.asc",
                    "limit": "2000",
                },
            )
            if tr_res.status_code == 200:
                for tr in tr_res.json():
                    sid = tr.get("strategy_id")
                    if sid:
                        trade_records_grouped.setdefault(sid, []).append(tr)
        except Exception:
            pass

        result = {}
        for sid, sessions in grouped.items():
            total_trades = sum(s.get("total_trades", 0) for s in sessions)
            winning = sum(s.get("winning_trades", 0) for s in sessions)
            total_pnl = sum(float(s.get("total_pnl", 0)) for s in sessions)
            win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
            tx_sigs = [s["tx_signature"] for s in sessions if s.get("tx_signature")]

            # trade_records 기반 equity curve (없으면 세션 폴백)
            equity_curve = []
            trades_for_sid = trade_records_grouped.get(sid, [])
            if trades_for_sid:
                cumulative = 0.0
                for tr in trades_for_sid:
                    cumulative += float(tr.get("pnl", 0))
                    equity_curve.append({"t": tr["created_at"], "v": round(cumulative, 2)})
            else:
                cumulative = 0.0
                for s in sessions:
                    cumulative += float(s.get("total_pnl", 0))
                    equity_curve.append({"t": s["created_at"], "v": round(cumulative, 2)})

            result[sid] = {
                "strategy_id": sid,
                "total_trades": total_trades,
                "winning_trades": winning,
                "win_rate": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "sessions": len(sessions),
                "tx_signatures": tx_sigs[:10],
                "verified": len(tx_sigs) > 0,
                "equity_curve": equity_curve,
            }
        return result
    except Exception as e:
        logger.warning(f"get_batch_strategy_performance_db 예외: {e}")
    return {}


async def get_trade_records_db(strategy_id: str, limit: int = 50) -> list:
    """전략의 개별 거래 기록을 DB에서 조회"""
    if not _is_available():
        return []
    try:
        client = _get_client()
        res = await client.get(
            _rest_url("trade_records"),
            headers=_headers(),
            params={
                "strategy_id": f"eq.{strategy_id}",
                "select": "side,entry_price,exit_price,pnl,exit_reason,created_at",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        return res.json() if res.status_code == 200 else []
    except Exception as e:
        logger.warning(f"get_trade_records_db 예외: {e}")
    return []


async def save_chat_message(strategy_id: str, role: str, content: str,
                            metadata: Optional[dict] = None) -> dict:
    if not _is_available():
        return {"id": "local-msg", "role": role, "content": content}
    data = {
        "strategy_id": strategy_id,
        "role": role,
        "content": content,
    }
    if metadata:
        data["metadata"] = metadata
    client = _get_client()
    res = await client.post(
        _rest_url("chat_messages"),
        headers=_headers(),
        json=data,
    )
    if res.status_code in (200, 201) and res.json():
        return res.json()[0]
    return {"id": "local-msg", "role": role, "content": content}


async def get_chat_messages(strategy_id: str) -> list:
    if not _is_available():
        return []
    client = _get_client()
    res = await client.get(
        _rest_url("chat_messages"),
        headers=_headers(),
        params={"strategy_id": f"eq.{strategy_id}", "select": "id,role,content,created_at", "limit": "50", "order": "created_at.desc", "order": "created_at"},
    )
    if res.status_code == 200:
        return res.json()
    return []


async def save_backtest_result(data: dict) -> dict:
    if not _is_available():
        return {"id": "local-backtest", **data}

    # DB 스키마: metrics는 JSONB 컬럼 하나, trade_log/ai_summary 컬럼 없음
    # trade_log, ai_summary는 metrics JSONB 안에 _키로 함께 저장
    metrics = dict(data.get("metrics") or {})
    if data.get("trade_log"):
        metrics["_trade_log"] = data["trade_log"]
    if data.get("ai_summary"):
        metrics["_ai_summary"] = data["ai_summary"]

    db_data = {
        "token_pair": data.get("token_pair"),
        "timeframe": data.get("timeframe"),
        "metrics": metrics,
        "equity_curve": data.get("equity_curve"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "parsed_strategy": data.get("parsed_strategy"),
    }
    if data.get("strategy_id"):
        db_data["strategy_id"] = data["strategy_id"]
    # None 값 제거
    db_data = {k: v for k, v in db_data.items() if v is not None}

    client = _get_client()
    res = await client.post(
        _rest_url("backtest_results"),
        headers=_headers(),
        json=db_data,
    )
    if res.status_code in (200, 201) and res.json():
        return res.json()[0]

    logger.error(f"Failed to save backtest to Supabase: {res.status_code} - {res.text}")
    return {"id": "local-backtest", **data}


def _enrich_backtest(row: dict, include_trade_log: bool = True) -> dict:
    """DB 행에서 metrics JSONB 안의 _trade_log, _ai_summary를 분리하여 최상위 필드로 노출"""
    if not row.get("metrics"):
        row["metrics"] = {}
    # _trade_log, _ai_summary를 metrics에서 꺼내서 별도 필드로 제공
    row["trade_log"] = row["metrics"].pop("_trade_log", [])
    row["ai_summary"] = row["metrics"].pop("_ai_summary", None)
    return row


async def get_backtest_by_id(backtest_id: str) -> Optional[dict]:
    if not _is_available():
        return None
    client = _get_client()
    res = await client.get(
        _rest_url("backtest_results"),
        headers=_headers(),
        params={"id": f"eq.{backtest_id}", "select": "*"},
    )
    if res.status_code == 200 and res.json():
        return _enrich_backtest(res.json()[0])
    return None

async def get_backtests_by_strategy_id(strategy_id: str) -> list:
    if not _is_available():
        return []
    client = _get_client()
    res = await client.get(
        _rest_url("backtest_results"),
        headers=_headers(),
        params={
            "strategy_id": f"eq.{strategy_id}",
            "select": "id,strategy_id,token_pair,timeframe,start_date,end_date,created_at,metrics,equity_curve,parsed_strategy",
            "order": "created_at.desc"
        },
    )
    if res.status_code == 200:
        return [_enrich_backtest(row, include_trade_log=False) for row in res.json()]
    return []

async def link_backtest_to_strategy(backtest_id: str, strategy_id: str) -> bool:
    """백테스트 결과의 strategy_id를 업데이트 (메인 챗에서 저장 후 연결)"""
    if not _is_available():
        return False
    client = _get_client()
    res = await client.patch(
        _rest_url("backtest_results"),
        headers=_headers(),
        params={"id": f"eq.{backtest_id}"},
        json={"strategy_id": strategy_id},
    )
    return res.status_code in (200, 204)


async def save_strategy_version(
    strategy_id: str,
    parsed_strategy: dict,
    mint_tx: str = "",
    mint_hash: str = "",
    mint_network: str = "devnet",
    label: str = "",
) -> Optional[dict]:
    """민팅 시점의 전략 스냅샷을 strategy_versions에 저장"""
    if not _is_available():
        return None
    try:
        # 현재 최대 버전 번호 조회
        client = _get_client()
        res = await client.get(
            _rest_url("strategy_versions"),
            headers=_headers(),
            params={
                "strategy_id": f"eq.{strategy_id}",
                "select": "version",
                "order": "version.desc",
                "limit": "1",
            },
        )
        existing = res.json() if res.status_code == 200 else []
        next_version = (existing[0]["version"] + 1) if existing else 1

        # 스냅샷 저장
        res = await client.post(
            _rest_url("strategy_versions"),
            headers=_headers(),
            json={
                "strategy_id": strategy_id,
                "version": next_version,
                "parsed_strategy": parsed_strategy,
                "mint_tx": mint_tx,
                "mint_hash": mint_hash,
                "mint_network": mint_network,
                "label": label or f"v{next_version}",
            },
        )
        if res.status_code in (200, 201) and res.json():
            return res.json()[0]
        logger.warning(f"strategy_version 저장 실패: {res.status_code} {res.text}")
        return None
    except Exception as e:
        logger.warning(f"save_strategy_version 예외: {e}")
        return None


async def get_strategy_versions(strategy_id: str) -> list:
    """전략의 모든 민팅 버전 조회 (최신순)"""
    if not _is_available():
        return []
    try:
        client = _get_client()
        res = await client.get(
            _rest_url("strategy_versions"),
            headers=_headers(),
            params={
                "strategy_id": f"eq.{strategy_id}",
                "select": "id,version,label,mint_tx,mint_hash,mint_network,created_at",
                "order": "version.desc",
            },
        )
        return res.json() if res.status_code == 200 else []
    except Exception as e:
        logger.warning(f"get_strategy_versions 예외: {e}")
        return []


async def get_strategy_version(version_id: str) -> Optional[dict]:
    """특정 버전의 전략 스냅샷 조회 (parsed_strategy 포함)"""
    if not _is_available():
        return None
    try:
        client = _get_client()
        res = await client.get(
            _rest_url("strategy_versions"),
            headers=_headers(),
            params={"id": f"eq.{version_id}", "select": "*"},
        )
        data = res.json() if res.status_code == 200 else []
        return data[0] if data else None
    except Exception as e:
        logger.warning(f"get_strategy_version 예외: {e}")
        return None


async def delete_backtest_by_id(backtest_id: str) -> bool:
    if not _is_available():
        return False
    client = _get_client()
    res = await client.delete(
        _rest_url("backtest_results"),
        headers=_headers(),
        params={"id": f"eq.{backtest_id}"},
    )
    return res.status_code in (200, 204)

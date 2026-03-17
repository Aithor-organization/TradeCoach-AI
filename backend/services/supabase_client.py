import logging
import httpx
from config import get_settings
from typing import Optional
from data.example_strategies import get_example_strategies, get_example_strategy_by_id

logger = logging.getLogger(__name__)
settings = get_settings()

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
        async with httpx.AsyncClient(timeout=5.0) as client:
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
        async with httpx.AsyncClient(timeout=5.0) as client:
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
        async with httpx.AsyncClient(timeout=5.0) as client:
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
    async with httpx.AsyncClient() as client:
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


async def get_or_create_user_by_email(email: str, name: str) -> Optional[dict]:
    """이메일로 사용자 조회 또는 생성 (MVP 간편 가입)"""
    if not _is_available():
        import uuid
        from datetime import datetime, timezone
        return {"id": str(uuid.uuid4()), "wallet_address": email, "display_name": name, "tier": "free", "created_at": datetime.now(timezone.utc).isoformat()}
    async with httpx.AsyncClient(timeout=5.0) as client:
        # 이메일로 기존 사용자 조회 (wallet_address 필드를 이메일로 활용)
        res = await client.get(
            _rest_url("users"),
            headers=_headers(),
            params={"wallet_address": f"eq.{email}", "select": "*"},
        )
        if res.status_code == 200 and res.json():
            return res.json()[0]
        # 신규 생성 (display_name이 스키마에 없을 수 있으므로 최소 필드만)
        res = await client.post(
            _rest_url("users"),
            headers=_headers(),
            json={"wallet_address": email, "tier": "free"},
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
            user["display_name"] = name
            return user
        logger.warning(f"Supabase user creation failed: {res.status_code} {res.text}")
        return None


async def get_strategies(user_id: Optional[str] = None) -> list:
    if not _is_available():
        return get_example_strategies()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            params: dict = {"select": "*", "order": "created_at.desc", "limit": "50"}
            if user_id:
                # 로그인 사용자: 본인 전략만 조회
                params["user_id"] = f"eq.{user_id}"
            res = await client.get(
                _rest_url("strategies"),
                headers=_headers(),
                params=params,
            )
            if res.status_code == 200:
                db_strategies = res.json()
                # DB 전략 + 예시 전략 합쳐서 반환
                return db_strategies + get_example_strategies()
            logger.error(f"get_strategies 실패: {res.status_code} {res.text}")
            return get_example_strategies()
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
        async with httpx.AsyncClient(timeout=5.0) as client:
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
    async with httpx.AsyncClient() as client:
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
    async with httpx.AsyncClient() as client:
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
    async with httpx.AsyncClient() as client:
        res = await client.delete(
            _rest_url("strategies"),
            headers=_headers(),
            params={"id": f"eq.{strategy_id}"},
        )
        return res.status_code == 200


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
    async with httpx.AsyncClient() as client:
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
    async with httpx.AsyncClient() as client:
        res = await client.get(
            _rest_url("chat_messages"),
            headers=_headers(),
            params={"strategy_id": f"eq.{strategy_id}", "select": "*", "order": "created_at"},
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

    async with httpx.AsyncClient() as client:
        res = await client.post(
            _rest_url("backtest_results"),
            headers=_headers(),
            json=db_data,
        )
        if res.status_code in (200, 201) and res.json():
            return res.json()[0]

        logger.error(f"Failed to save backtest to Supabase: {res.status_code} - {res.text}")
        return {"id": "local-backtest", **data}


def _enrich_backtest(row: dict) -> dict:
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
    async with httpx.AsyncClient() as client:
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
    async with httpx.AsyncClient() as client:
        res = await client.get(
            _rest_url("backtest_results"),
            headers=_headers(),
            params={
                "strategy_id": f"eq.{strategy_id}",
                "select": "*",
                "order": "created_at.desc"
            },
        )
        if res.status_code == 200:
            return [_enrich_backtest(row) for row in res.json()]
        return []

async def link_backtest_to_strategy(backtest_id: str, strategy_id: str) -> bool:
    """백테스트 결과의 strategy_id를 업데이트 (메인 챗에서 저장 후 연결)"""
    if not _is_available():
        return False
    async with httpx.AsyncClient() as client:
        res = await client.patch(
            _rest_url("backtest_results"),
            headers=_headers(),
            params={"id": f"eq.{backtest_id}"},
            json={"strategy_id": strategy_id},
        )
        return res.status_code in (200, 204)


async def delete_backtest_by_id(backtest_id: str) -> bool:
    if not _is_available():
        return False
    async with httpx.AsyncClient() as client:
        res = await client.delete(
            _rest_url("backtest_results"),
            headers=_headers(),
            params={"id": f"eq.{backtest_id}"},
        )
        return res.status_code in (200, 204)

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


async def get_strategies(user_id: Optional[str] = None) -> list:
    if not _is_available():
        return get_example_strategies()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            params: dict = {"select": "*", "order": "created_at.desc", "limit": "50"}
            if user_id:
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
    async with httpx.AsyncClient() as client:
        res = await client.post(
            _rest_url("backtest_results"),
            headers=_headers(),
            json=data,
        )
        if res.status_code in (200, 201) and res.json():
            return res.json()[0]
        return {"id": "local-backtest", **data}


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
            return res.json()[0]
        return None

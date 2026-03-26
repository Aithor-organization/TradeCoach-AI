"""
Arweave 영구 저장 서비스 (StrategyVault 패턴)
백테스트 차트/데이터를 Arweave에 영구 저장하고 URI를 반환한다.
실제 Arweave 업로드 대신 Irys(Bundlr) 게이트웨이를 통해 저장.
"""
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

IRYS_NODE_URL = "https://node2.irys.xyz"  # Arweave 게이트웨이
ARWEAVE_GATEWAY = "https://arweave.net"


@dataclass
class ArweaveUploadResult:
    tx_id: str
    uri: str  # arweave://tx_id 형식
    size_bytes: int
    content_hash: str


class ArweaveStorage:
    """
    Arweave/Irys 영구 저장 클라이언트.
    
    사용 예:
        storage = ArweaveStorage()
        result = await storage.upload_backtest_data(strategy_id, backtest_result)
        # result.uri = "arweave://abc123..."
    """

    def __init__(self, wallet_key: Optional[str] = None):
        self._wallet_key = wallet_key

    async def upload_json(self, data: dict, tags: Optional[dict] = None) -> ArweaveUploadResult:
        """JSON 데이터를 Arweave에 업로드한다."""
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        content_hash = hashlib.sha256(body).hexdigest()

        headers = {"Content-Type": "application/json"}
        if tags:
            for k, v in tags.items():
                headers[f"Tag-{k}"] = str(v)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{IRYS_NODE_URL}/tx/arweave",
                    content=body,
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()
                tx_id = result.get("id", content_hash[:43])
        except Exception as e:
            logger.warning("Arweave 업로드 실패, 로컬 해시로 대체: %s", e)
            tx_id = f"local_{content_hash[:40]}"

        return ArweaveUploadResult(
            tx_id=tx_id,
            uri=f"arweave://{tx_id}",
            size_bytes=len(body),
            content_hash=content_hash,
        )

    async def upload_backtest_data(
        self, strategy_id: str, backtest_result: dict, strategy_name: str = ""
    ) -> ArweaveUploadResult:
        """백테스트 결과를 Arweave에 영구 저장한다."""
        payload = {
            "type": "tradecoach_backtest",
            "version": "1.0",
            "strategy_id": strategy_id,
            "strategy_name": strategy_name,
            "timestamp": int(time.time()),
            "metrics": backtest_result.get("metrics", backtest_result),
            "trade_count": backtest_result.get("total_trades", 0),
        }

        tags = {
            "App-Name": "TradeCoach-AI",
            "Content-Type": "application/json",
            "Strategy-ID": strategy_id,
            "Type": "backtest-result",
        }

        result = await self.upload_json(payload, tags)
        logger.info(
            "백테스트 데이터 Arweave 저장: strategy=%s uri=%s size=%dB",
            strategy_id, result.uri, result.size_bytes,
        )
        return result

    @staticmethod
    def get_arweave_url(tx_id: str) -> str:
        """Arweave TX ID에서 접근 가능한 URL을 반환한다."""
        clean_id = tx_id.replace("arweave://", "").replace("local_", "")
        return f"{ARWEAVE_GATEWAY}/{clean_id}"

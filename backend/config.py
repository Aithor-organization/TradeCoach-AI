import logging
import os

from pydantic_settings import BaseSettings
from functools import lru_cache

logger = logging.getLogger(__name__)

_DEV_SECRET = "dev-secret-change-in-production"


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""

    # OpenRouter (임베딩용)
    openrouter_api_key: str = ""

    # Birdeye
    birdeye_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # JWT
    jwt_secret: str = _DEV_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24시간

    # CORS
    cors_origins: str = "http://localhost:3000,https://trade-coach-ai.vercel.app"

    # Solana
    solana_rpc_url: str = "https://api.devnet.solana.com"
    solana_network: str = "devnet"
    helius_api_key: str = ""
    solana_keypair_path: str = "~/.config/solana/id.json"

    # StrategyVault Program IDs (Devnet)
    program_strategy_registry: str = "6EuhmRPHqN4r6SoP8anEpm2ZmVuQoHLLWre4zEPdc6Bo"
    program_signal_recorder: str = "HydMVYPxrrCkFAnwaZLKeYzPoEvF1qSSDYnX1fSC2J89"
    program_strategy_marketplace: str = "BKmM7ZHuKmg6f5FQbv6rTF44sJkYNR2UsSbvRFGgnmU1"
    program_performance_verifier: str = "J3LeviD4zd9y5izVHLLwgopvEM82A9aUdgXi29wioNCL"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    s = Settings()

    env = os.getenv("ENV", "development")
    is_prodlike = env in ("production", "staging")

    # 🔴 프로덕션/스테이징에서 누락되면 앱 기동 자체를 차단 (fail-fast).
    # 빈 값으로 올라오면 첫 요청에서 미묘한 500/401이 튀어 디버깅이 어려움.
    missing: list[str] = []
    if not s.jwt_secret or s.jwt_secret == _DEV_SECRET:
        missing.append("JWT_SECRET")
    if not s.supabase_url:
        missing.append("SUPABASE_URL")
    if not s.supabase_service_key:
        missing.append("SUPABASE_SERVICE_KEY")
    if not s.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    # Solana 키페어는 파일 경로라 값 존재만 확인 (실재 여부는 anchor_client가 lazy-validate)
    if not s.solana_rpc_url:
        missing.append("SOLANA_RPC_URL")

    if is_prodlike and missing:
        raise ValueError(
            f"프로덕션/스테이징 환경에서 필수 환경변수 누락: {', '.join(missing)}. "
            "Railway/Vercel 대시보드에서 설정 후 재배포하세요."
        )

    if missing and not is_prodlike:
        logger.warning(
            "⚠️ 개발 모드에서 %d개 환경변수가 기본값/공백입니다: %s. 일부 기능이 제한될 수 있습니다.",
            len(missing),
            ", ".join(missing),
        )

    return s

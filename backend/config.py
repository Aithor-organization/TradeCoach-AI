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

    # 프로덕션 환경에서 기본 JWT 시크릿 사용 경고
    if s.jwt_secret == _DEV_SECRET:
        env = os.getenv("ENV", "development")
        if env in ("production", "staging"):
            raise ValueError(
                "JWT_SECRET이 기본값입니다. 프로덕션에서는 반드시 환경변수로 안전한 시크릿을 설정하세요."
            )
        logger.warning(
            "⚠️ JWT_SECRET이 기본 개발용 값입니다. 프로덕션 배포 전 반드시 변경하세요."
        )

    return s

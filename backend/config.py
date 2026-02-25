from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""

    # Birdeye
    birdeye_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24시간

    # CORS
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

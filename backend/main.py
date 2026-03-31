import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import get_settings
from routers import auth, chat, strategy, backtest, market, optimize, trading, blockchain, admin, marketplace

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 RAG 지식 베이스 로드 (실패해도 앱은 정상 시작)
    try:
        from services.rag import load_knowledge_base, get_stats
        load_knowledge_base()
        stats = get_stats()
        logger.info(f"RAG 지식 베이스 로드 완료: {stats['total_documents']}개 문서")
    except Exception as e:
        logger.warning(f"RAG 지식 베이스 로드 실패 (앱은 정상 작동): {e}")
    yield


app = FastAPI(
    title="TradeCoach AI",
    description=(
        "AI-powered Solana trading coach.\n\n"
        "## Features\n"
        "- **Auth**: Phantom wallet authentication (nonce + signature → JWT)\n"
        "- **Chat**: Gemini 3.1 Pro coaching with RAG knowledge base\n"
        "- **Strategy**: Natural language → structured trading strategy\n"
        "- **Backtest**: VectorBT-based backtesting with AI analysis\n"
        "- **Market**: Real-time token prices via Jupiter Quote API"
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "auth", "description": "Phantom 지갑 인증 및 JWT 발급"},
        {"name": "chat", "description": "AI 코칭 채팅 (텍스트, 이미지, 스트리밍)"},
        {"name": "strategy", "description": "트레이딩 전략 파싱, 저장, CRUD"},
        {"name": "backtest", "description": "백테스트 실행 및 AI 분석"},
        {"name": "market", "description": "Jupiter 기반 실시간 토큰 가격"},
    ],
)

# Rate Limiting — 인증된 사용자는 user_id 기반, 미인증은 IP 기반
def _rate_limit_key_func(request: Request) -> str:
    """인증된 사용자는 JWT의 user_id, 미인증은 클라이언트 IP로 Rate Limit 키 생성."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from jose import jwt as _jwt
            token = auth_header[7:]
            payload = _jwt.decode(
                token, settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},  # 키 추출만 — 만료 무관
            )
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    return get_remote_address(request)

# limiter를 사용자 인식 키 함수로 재생성
from slowapi import Limiter
user_aware_limiter = Limiter(key_func=_rate_limit_key_func)
app.state.limiter = user_aware_limiter
# auth 라우터의 limiter도 교체 (엔드포인트별 제한은 데코레이터에서 직접 설정)
auth.limiter = user_aware_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"요청 검증 실패: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "type": "validation_error"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback; traceback.print_exc()
    logger.error(f"처리되지 않은 예외 [{request.method} {request.url.path}]: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}", "type": "server_error"})


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
app.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(optimize.router, prefix="/optimize", tags=["optimize"])
app.include_router(trading.router, prefix="/trading", tags=["trading"])
app.include_router(blockchain.router, prefix="/blockchain", tags=["blockchain"])
app.include_router(admin.router)
app.include_router(marketplace.router)


@app.get("/health", tags=["system"])
async def health_check():
    from services.rag import get_stats
    from services.supabase_client import _is_available
    rag_stats = get_stats()
    return {
        "status": "ok",
        "version": "0.2.0",
        "database": "connected" if _is_available() else "unavailable",
        "rag": {"documents": rag_stats["total_documents"]},
    }

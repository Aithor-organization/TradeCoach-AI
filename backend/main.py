import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings
from routers import auth, chat, strategy, backtest, market

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

# Rate Limiting 예외 핸들러
app.state.limiter = auth.limiter
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
    logger.error(f"처리되지 않은 예외 [{request.method} {request.url.path}]: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다.", "type": "server_error"})


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
app.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
app.include_router(market.router, prefix="/market", tags=["market"])


@app.get("/health")
async def health_check():
    from services.rag import get_stats
    rag_stats = get_stats()
    return {
        "status": "ok",
        "version": "0.1.0",
        "rag": {"documents": rag_stats["total_documents"]},
    }

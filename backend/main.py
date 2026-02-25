import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import auth, chat, strategy, backtest

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 RAG 지식 베이스 로드
    from services.rag import load_knowledge_base, get_stats
    load_knowledge_base()
    stats = get_stats()
    logger.info(f"RAG 지식 베이스 로드 완료: {stats['total_documents']}개 문서")
    yield


app = FastAPI(
    title="TradeCoach AI",
    description="AI 트레이딩 코치 백엔드 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
app.include_router(backtest.router, prefix="/backtest", tags=["backtest"])


@app.get("/health")
async def health_check():
    from services.rag import get_stats
    rag_stats = get_stats()
    return {
        "status": "ok",
        "version": "0.1.0",
        "rag": {"documents": rag_stats["total_documents"]},
    }

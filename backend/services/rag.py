"""RAG 서비스 - ChromaDB + OpenAI Embedding 기반 지식 검색"""

import json
import logging
from pathlib import Path

import chromadb
from openai import OpenAI

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# OpenRouter 클라이언트 (OpenAI 호환 API)
_openai = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

# ChromaDB 클라이언트 (로컬 영구 저장)
_DB_PATH = str(Path(__file__).parent.parent / "data" / "chromadb")
_client = chromadb.PersistentClient(path=_DB_PATH)
_collection = _client.get_or_create_collection(
    name="trading_knowledge_v2",
    metadata={"hnsw:space": "cosine"},
)

# OpenAI Embedding 모델
_EMBED_MODEL = "text-embedding-3-small"


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """OpenAI Embedding API로 텍스트 임베딩 생성"""
    response = _openai.embeddings.create(
        model=_EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def _embed_query(text: str) -> list[float]:
    """검색 쿼리 임베딩"""
    response = _openai.embeddings.create(
        model=_EMBED_MODEL,
        input=text,
    )
    return response.data[0].embedding


def add_documents(
    documents: list[str],
    metadatas: list[dict] | None = None,
    ids: list[str] | None = None,
) -> int:
    """지식 문서를 벡터 DB에 추가"""
    if not documents:
        return 0

    if ids is None:
        existing = _collection.count()
        ids = [f"doc_{existing + i}" for i in range(len(documents))]

    embeddings = _embed_texts(documents)
    _collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas or [{}] * len(documents),
        ids=ids,
    )
    logger.info(f"RAG: {len(documents)}개 문서 추가 (총 {_collection.count()}개)")
    return len(documents)


def search(query: str, n_results: int = 3) -> list[dict]:
    """쿼리와 관련된 지식 검색"""
    if not settings.openrouter_api_key or _collection.count() == 0:
        return []

    query_embedding = _embed_query(query)
    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, _collection.count()),
    )

    docs = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        distance = results["distances"][0][i] if results["distances"] else 0
        docs.append({
            "content": doc,
            "metadata": meta,
            "relevance": 1 - distance,  # cosine distance → similarity
        })
    return docs


def build_rag_context(query: str, n_results: int = 3, min_relevance: float = 0.3) -> str:
    """검색 결과를 Gemini 프롬프트용 컨텍스트 문자열로 변환"""
    results = search(query, n_results=n_results)
    if not results:
        return ""

    relevant = [r for r in results if r["relevance"] >= min_relevance]
    if not relevant:
        return ""

    parts = ["[참고 자료]"]
    for r in relevant:
        category = r["metadata"].get("category", "")
        label = f" ({category})" if category else ""
        parts.append(f"- {r['content']}{label}")

    return "\n".join(parts)


def get_stats() -> dict:
    """벡터 DB 상태 조회"""
    return {
        "total_documents": _collection.count(),
        "db_path": _DB_PATH,
    }


def load_knowledge_base():
    """초기 트레이딩 지식 베이스 로드 (이미 있으면 스킵)"""
    if not settings.openrouter_api_key:
        logger.warning("RAG: OPENROUTER_API_KEY 미설정, 지식 베이스 로드 건너뜀")
        return

    if _collection.count() > 0:
        logger.info(f"RAG: 지식 베이스 이미 로드됨 ({_collection.count()}개 문서)")
        return

    knowledge_file = Path(__file__).parent.parent / "data" / "trading_knowledge.json"
    if not knowledge_file.exists():
        logger.warning("RAG: trading_knowledge.json 파일 없음, 기본 지식 로드")
        _load_default_knowledge()
        return

    with open(knowledge_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    metadatas = []
    ids = []
    for i, item in enumerate(data):
        documents.append(item["content"])
        metadatas.append({"category": item.get("category", "general")})
        ids.append(f"kb_{i}")

    add_documents(documents, metadatas, ids)
    logger.info(f"RAG: 지식 베이스 로드 완료 ({len(documents)}개)")


def _load_default_knowledge():
    """기본 트레이딩 교육 지식 (파일 없을 때 폴백)"""
    knowledge = _get_default_knowledge()

    documents = [k["content"] for k in knowledge]
    metadatas = [{"category": k["category"]} for k in knowledge]
    ids = [f"default_{i}" for i in range(len(knowledge))]

    add_documents(documents, metadatas, ids)


def _get_default_knowledge() -> list[dict]:
    """기본 트레이딩 지식 데이터"""
    return [
        # 기술적 지표
        {
            "category": "indicator",
            "content": "RSI(상대강도지수)는 0~100 범위의 모멘텀 지표입니다. 일반적으로 RSI 30 이하는 과매도(매수 기회), 70 이상은 과매수(매도 기회)로 해석합니다. 기본 기간은 14이며, 단기(7~9)는 민감하고 장기(21~25)는 안정적입니다. RSI 다이버전스(가격은 신고가인데 RSI는 하락)는 추세 반전의 강력한 신호입니다.",
        },
        {
            "category": "indicator",
            "content": "이동평균(MA)은 추세 판단의 기본 지표입니다. 단기(5~20일) MA가 장기(50~200일) MA를 상향 돌파하면 골든크로스(매수 신호), 하향 돌파하면 데드크로스(매도 신호)입니다. EMA(지수이동평균)는 SMA보다 최근 가격에 가중치를 더 두어 추세 변화에 빠르게 반응합니다.",
        },
        {
            "category": "indicator",
            "content": "볼린저 밴드(BB)는 20일 SMA를 중심으로 ±2 표준편차 밴드를 그립니다. 밴드 수축(스퀴즈)은 변동성 감소 → 큰 움직임 예고입니다. 하단 밴드 터치 후 반등은 매수 기회, 상단 밴드 터치 후 하락은 매도 기회가 될 수 있습니다. 밴드 폭이 넓으면 변동성이 높은 상태입니다.",
        },
        {
            "category": "indicator",
            "content": "MACD(이동평균수렴확산)는 12일 EMA - 26일 EMA로 계산합니다. MACD 라인이 시그널 라인(9일 EMA)을 상향 돌파하면 매수 신호, 하향 돌파하면 매도 신호입니다. 히스토그램이 양에서 음으로 전환되면 모멘텀 약화를 의미합니다. 0선 위에서의 골든크로스가 더 강한 매수 신호입니다.",
        },
        {
            "category": "indicator",
            "content": "거래량(Volume)은 가격 움직임의 신뢰도를 확인하는 핵심 지표입니다. 가격 상승 + 거래량 증가 = 강한 상승 추세. 가격 상승 + 거래량 감소 = 추세 약화 경고. 갑작스러운 거래량 급증(평균의 3배 이상)은 세력의 움직임이나 중요 이벤트를 시사합니다. 솔라나 DEX에서는 온체인 거래량을 직접 확인할 수 있어 더 신뢰할 수 있습니다.",
        },
        {
            "category": "indicator",
            "content": "스토캐스틱 오실레이터는 현재 가격이 일정 기간 최고/최저가 대비 어디에 있는지 보여줍니다. %K가 80 이상이면 과매수, 20 이하면 과매도입니다. %K가 %D를 상향 돌파하면 매수 신호입니다. RSI와 함께 사용하면 더 정확한 진입 타이밍을 잡을 수 있습니다.",
        },
        # 리스크 관리
        {
            "category": "risk_management",
            "content": "포지션 사이징의 핵심 규칙: 한 번의 거래에서 전체 포트폴리오의 1~2% 이상 리스크를 걸지 마세요. 예를 들어 $1,000 포트폴리오에서 2% 규칙 적용 시 한 거래의 최대 손실은 $20입니다. 이를 역산하면 진입가와 손절가의 차이로 적정 포지션 크기를 계산할 수 있습니다.",
        },
        {
            "category": "risk_management",
            "content": "손절(Stop Loss)은 반드시 진입 전에 설정해야 합니다. 감정적 판단으로 손절을 미루면 작은 손실이 큰 손실로 확대됩니다. 일반적으로 단기 트레이딩에서는 -3%~-5%, 스윙 트레이딩에서는 -7%~-10% 손절이 적합합니다. 트레일링 스탑(추적 손절)을 활용하면 수익을 보호하면서 추세를 따를 수 있습니다.",
        },
        {
            "category": "risk_management",
            "content": "리스크 대비 보상 비율(R:R)은 최소 1:2 이상을 권장합니다. 손절이 -5%라면 목표 수익은 최소 +10% 이상이어야 합니다. R:R이 1:3이면 승률 25%로도 수익이 가능합니다. 높은 R:R 비율의 전략을 선택하면 승률이 낮아도 장기적으로 수익을 낼 수 있습니다.",
        },
        {
            "category": "risk_management",
            "content": "최대 낙폭(MDD, Maximum Drawdown)은 포트폴리오 최고점 대비 최저점 하락률입니다. MDD가 -20% 이상이면 원금 회복에 +25%가 필요합니다. MDD -50%이면 +100%(2배)가 필요합니다. 전문 트레이더는 MDD를 -20% 이내로 관리합니다. 샤프 비율 1.0 이상이면 리스크 대비 양호한 수익률입니다.",
        },
        {
            "category": "risk_management",
            "content": "분산 투자와 상관관계: 같은 섹터 코인에 집중 투자하면 분산 효과가 없습니다. 솔라나 DEX에서는 SOL, 밈코인, DeFi 토큰, 유틸리티 토큰 등 다른 카테고리에 분산하세요. 동시에 3개 이상의 포지션을 열 때는 각 포지션의 리스크 합계가 전체 포트폴리오의 5%를 넘지 않도록 관리하세요.",
        },
        # 전략 패턴
        {
            "category": "strategy",
            "content": "모멘텀 전략: 강한 추세에 편승하는 전략입니다. 진입 조건으로 RSI 50 이상 + 거래량 증가 + 가격이 20일 MA 위에 있을 때 매수합니다. 추세가 약해지는 신호(RSI 하락 반전, 거래량 감소)가 나타나면 부분 익절합니다. 솔라나에서는 급등하는 밈코인에 자주 적용되지만, 급반전 리스크가 높으므로 타이트한 손절이 필수입니다.",
        },
        {
            "category": "strategy",
            "content": "평균 회귀 전략: 과매도 또는 과매수 상태에서 평균으로 돌아올 것을 기대하는 전략입니다. RSI 30 이하에서 매수, 70 이상에서 매도합니다. 볼린저 밴드 하단 터치 시 매수, 상단 터치 시 매도할 수 있습니다. 레인지 장세(횡보)에서 효과적이지만, 강한 추세장에서는 큰 손실을 볼 수 있으므로 추세 필터와 함께 사용하세요.",
        },
        {
            "category": "strategy",
            "content": "브레이크아웃 전략: 주요 지지/저항선을 돌파할 때 진입합니다. 거래량 확인이 핵심입니다 - 거래량 동반 돌파는 진짜 돌파, 거래량 없는 돌파는 페이크아웃(가짜 돌파)일 확률이 높습니다. 돌파 후 되돌림(풀백)에서 진입하면 더 안전합니다. 솔라나 DEX에서는 유동성이 낮은 토큰의 돌파는 슬리피지가 클 수 있으니 주의하세요.",
        },
        {
            "category": "strategy",
            "content": "DCA(달러 코스트 애버리징) 전략: 정해진 금액을 정기적으로 매수하는 전략입니다. 타이밍을 맞추려 하지 않고, 시간에 걸쳐 평균 매입가를 낮춥니다. 장기적으로 우상향하는 자산에 효과적입니다. 변동성이 큰 솔라나 토큰에서 DCA는 심리적 안정감을 줍니다. 급등 시 FOMO 방지, 급락 시 패닉셀 방지 효과가 있습니다.",
        },
        # 솔라나/DEX 특화
        {
            "category": "solana_dex",
            "content": "솔라나 DEX(탈중앙화 거래소) 트레이딩 시 슬리피지에 주의하세요. 유동성이 낮은 토큰은 큰 주문 시 예상보다 불리한 가격으로 체결됩니다. Jupiter Aggregator를 사용하면 여러 DEX의 유동성을 통합해 최적의 가격을 얻을 수 있습니다. 최소 유동성 $100K 이상인 토큰을 권장합니다.",
        },
        {
            "category": "solana_dex",
            "content": "솔라나 밈코인 트레이딩 주의사항: 밈코인은 펀더멘탈 없이 커뮤니티와 바이럴에 의존합니다. 단기간 10x~100x 수익이 가능하지만, 99% 하락도 흔합니다. 반드시 잃어도 되는 금액만 투자하세요. 진입 시점은 소셜 미디어 트렌드, 온체인 거래량, 유동성 변화를 확인하세요. 탈출 전략(익절 기준)을 미리 정해두는 것이 핵심입니다.",
        },
        {
            "category": "solana_dex",
            "content": "온체인 데이터 활용: 솔라나의 장점은 모든 거래가 블록체인에 기록된다는 것입니다. 고래 지갑의 움직임(대량 매수/매도), DEX 거래량 추세, 신규 유동성 풀 생성을 모니터링하세요. Birdeye, DEXScreener 같은 도구로 실시간 온체인 데이터를 확인할 수 있습니다. 갑작스런 유동성 제거(러그풀)를 감지하는 것이 중요합니다.",
        },
        # 트레이딩 심리
        {
            "category": "psychology",
            "content": "FOMO(Fear Of Missing Out, 놓칠까봐 두려움)는 가장 위험한 트레이딩 감정입니다. 급등하는 코인을 보고 추격 매수하면 고점에 물리기 쉽습니다. 해결법: 미리 정한 전략의 진입 조건이 충족될 때만 매수하세요. '이미 놓친 기회'에 미련을 갖지 말고, 다음 기회를 기다리세요. 시장은 항상 새로운 기회를 줍니다.",
        },
        {
            "category": "psychology",
            "content": "손실 회피 편향: 인간은 같은 금액의 이익보다 손실에 2배 더 민감합니다. 이로 인해 수익 중인 포지션은 너무 빨리 익절하고, 손실 중인 포지션은 너무 오래 들고 있는 경향이 있습니다. 해결법: 진입 전에 익절/손절 기준을 명확히 설정하고, 감정과 무관하게 기계적으로 실행하세요.",
        },
        {
            "category": "psychology",
            "content": "오버트레이딩(과매매) 경고 신호: 하루에 10번 이상 거래, 손실 후 즉시 복구하려는 거래, 전략 없이 직감으로 거래, 계획보다 큰 포지션 크기. 해결법: 하루 최대 거래 횟수를 정하고(예: 3회), 거래 일지를 작성하세요. 연속 3번 손절 시 당일 거래를 중단하는 규칙을 만드세요.",
        },
        # 백테스트 해석
        {
            "category": "backtest",
            "content": "백테스트 결과 해석 시 주의할 점: 과거 성과가 미래 수익을 보장하지 않습니다. 과최적화(overfitting)를 경계하세요 - 너무 많은 파라미터를 조정하면 과거 데이터에만 맞는 전략이 됩니다. 충분한 거래 횟수(최소 30회 이상)가 있어야 통계적으로 의미가 있습니다. Out-of-sample 테스트(학습에 사용하지 않은 기간)로 검증하세요.",
        },
        {
            "category": "backtest",
            "content": "핵심 백테스트 지표 해석: 1) 총 수익률 - 기간 수익의 절대값. 2) 샤프 비율 - 1.0 이상이면 양호, 2.0 이상이면 우수. 3) 최대 낙폭(MDD) - -20% 이내가 안전. 4) 승률 - 50% 이상이 이상적이지만 R:R 비율에 따라 30%도 수익 가능. 5) 평균 보유 기간 - 전략 유형과 일치하는지 확인. 6) 거래 횟수 - 수수료 영향 평가에 중요.",
        },
    ]

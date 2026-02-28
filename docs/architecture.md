# TradeCoach AI — MVP 기술 아키텍처 설계서

> README.md를 그대로 유지하면서, 기술 아키텍처 갭을 채우는 구현 설계 문서
> UI 디자인 참조: `pencil-new.pen`

---

## 1. 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────┐
│                    사용자 브라우저                         │
│  Next.js 15 (App Router) + Tailwind CSS v4              │
│  Phantom Wallet Adapter                                  │
└────────────────┬───────────────────┬────────────────────┘
                 │ REST API           │ Wallet RPC
                 ▼                    ▼
┌────────────────────────┐  ┌─────────────────────────┐
│   FastAPI (Railway)    │  │  Solana Mainnet (Helius) │
│                        │  └─────────────────────────┘
│  ┌──────────────────┐  │
│  │ Gemini 3.1 Pro   │  │
│  │ - 전략 파싱       │  │
│  │ - AI 코칭        │  │
│  │ - 이미지 분석     │  │
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ 백테스트 엔진     │  │
│  │ (VectorBT+pandas)│  │
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ Binance REST API │  │
│  │ (OHLCV 데이터)   │  │
│  └──────────────────┘  │
│  ┌──────────────────┐  │
│  │ Jupiter Quote API│  │
│  │ (실시간 가격)     │  │
│  └──────────────────┘  │
└────────────┬───────────┘
             │
             ▼
┌────────────────────────┐
│  Supabase (PostgreSQL) │
│  - 사용자, 전략, 백테스트│
│  - Auth (지갑 기반)     │
└────────────────────────┘
```

### 배포 구조

| 서비스 | 플랫폼 | 이유 |
|--------|--------|------|
| 프론트엔드 | Vercel | Next.js 최적 호스팅, 글로벌 CDN |
| 백엔드 API | Railway | Python FastAPI, 항시 기동, Docker 지원 |
| DB | Supabase | PostgreSQL + Auth + Realtime, 무료 티어 충분 |
| Solana RPC | Helius | 무료 티어 50K req/day, 안정적 |

---

## 2. 프론트엔드 아키텍처

### 2-1. 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Next.js | 15 (App Router) | SSR/SSG, 라우팅, API Route |
| Tailwind CSS | v4 | 스타일링 (pencil 디자인 기반) |
| TypeScript | 5.x | 타입 안전성 |
| Zustand | 5.x | 경량 상태 관리 |
| @solana/wallet-adapter-react | latest | Phantom 지갑 연동 |
| react-markdown | latest | AI 코칭 메시지 렌더링 |
| lightweight-charts | latest | 백테스트 차트 시각화 |

### 2-2. 디렉토리 구조

```
frontend/
├── app/
│   ├── layout.tsx              # 루트 레이아웃 (다크 테마, WalletProvider)
│   ├── page.tsx                # 랜딩 페이지 (pencil 디자인)
│   ├── chat/
│   │   └── page.tsx            # 메인 채팅 UI (전략 빌더 + AI 코칭)
│   └── strategies/
│       ├── page.tsx            # 전략 목록 (내 전략 + 예시 템플릿)
│       └── [id]/page.tsx       # 전략 상세 (백테스트 + AI 코칭 탭)
├── components/
│   ├── layout/
│   │   ├── Navigation.tsx      # 상단 네비게이션
│   │   └── Footer.tsx          # 푸터
│   ├── landing/
│   │   ├── Hero.tsx            # 히어로 섹션
│   │   ├── ChatMockup.tsx      # 채팅 목업 프리뷰
│   │   ├── HowItWorks.tsx      # 4단계 설명
│   │   ├── Features.tsx        # 핵심 기능 그리드
│   │   ├── Stats.tsx           # 통계 섹션
│   │   ├── Pricing.tsx         # 가격 플랜
│   │   └── FinalCTA.tsx        # 최종 CTA
│   ├── chat/
│   │   ├── ChatWindow.tsx      # 채팅 메시지 목록 (마크다운 렌더링)
│   │   ├── ChatInput.tsx       # 메시지 입력 (자동 리사이즈 textarea)
│   │   ├── ImagePreview.tsx    # 첨부 이미지 미리보기/삭제
│   │   ├── StrategyCard.tsx    # 전략 카드 (투자금 입력 포함)
│   │   ├── StrategyChatPanel.tsx # 전략 상세 페이지용 AI 코칭 채팅
│   │   ├── BacktestResult.tsx  # 백테스트 결과 메트릭스
│   │   ├── BacktestChart.tsx   # 자산곡선 차트 (lightweight-charts)
│   │   ├── BacktestSummary.tsx # AI 분석 리포트 + 빠른 개선 버튼
│   │   └── TradeLogTable.tsx   # 거래 내역 테이블
│   ├── wallet/
│   │   ├── WalletProvider.tsx  # Solana 지갑 프로바이더
│   │   ├── WalletConnectButton.tsx # 지갑 연결 + 잔액 표시
│   │   └── WalletBalance.tsx   # SOL 잔액 조회
│   ├── market/
│   │   └── TokenPrices.tsx     # 실시간 토큰 가격 위젯 (Jupiter)
│   └── common/
│       ├── Button.tsx          # 공통 버튼
│       ├── ErrorBoundary.tsx   # 에러 바운더리
│       ├── OnboardingBanner.tsx # 온보딩 배너
│       ├── Skeleton.tsx        # 로딩 스켈레톤
│       └── Toast.tsx           # 토스트 알림
├── lib/
│   ├── api.ts                  # FastAPI 호출 래퍼 (모든 엔드포인트)
│   └── types.ts                # 공유 타입 정의
├── stores/
│   └── chatStore.ts            # 채팅 상태 (Zustand)
└── styles/
    └── globals.css             # Tailwind 설정
```

### 2-3. 페이지 구성 (pencil 디자인 기반)

**랜딩 페이지** (`/`) — pencil-new.pen 그대로 구현:
1. Navigation (반투명 배경, 시안 액센트)
2. Hero Section (그라디언트 배지, 64px 헤드라인)
3. Product Preview (채팅 목업)
4. How It Works (4단계 카드)
5. Features Grid (3+2 레이아웃)
6. Stats Section (4개 지표)
7. Pricing (Free/Pro 2컬럼)
8. Final CTA (그라디언트 배경)
9. Footer

**채팅 페이지** (`/chat`) — MVP 핵심:
- 채팅 대화 영역 (전체 폭)
- AI 메시지에 전략 카드, 백테스트 차트 인라인 렌더링
- 하단: 입력 바 (텍스트 입력 + 이미지 첨부 + 전송 버튼)
- 이미지 첨부: 차트 캡처/스크린샷을 드래그 & 드롭 또는 클립보드 붙여넣기

---

## 3. 백엔드 아키텍처

### 3-1. 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.12 | 런타임 |
| FastAPI | 0.115+ | REST API 프레임워크 |
| google-genai | latest | Gemini 3.1 Pro SDK |
| vectorbt | 0.26+ | 백테스트 엔진 |
| pandas | 2.x | 데이터 처리 |
| httpx | latest | 외부 API 호출 (Binance, Jupiter) |
| supabase-py | latest | DB 클라이언트 |
| pydantic | 2.x | 데이터 검증 |

### 3-2. 디렉토리 구조

```
backend/
├── main.py                     # FastAPI 앱 진입점 + 헬스체크
├── config.py                   # 환경변수, 설정
├── dependencies.py             # FastAPI 의존성 (인증 등)
├── routers/
│   ├── auth.py                 # 지갑 기반 인증 API
│   ├── chat.py                 # 채팅/AI 코칭 API (SSE 스트리밍 포함)
│   ├── strategy.py             # 전략 CRUD + 포크 API
│   ├── backtest.py             # 백테스트 실행/분석 API
│   └── market.py               # 실시간 시장 가격 API (Jupiter)
├── services/
│   ├── gemini.py               # Gemini AI 연동 (파싱, 코칭, 분석)
│   ├── backtest_engine.py      # VectorBT 백테스트 로직
│   ├── binance.py              # Binance OHLCV 데이터 수집
│   ├── birdeye.py              # Birdeye 토큰 주소 매핑
│   ├── jupiter.py              # Jupiter Quote API (실시간 가격)
│   ├── market_data.py          # 시장 데이터 통합 서비스
│   ├── coaching.py             # AI 코칭 로직
│   ├── rag.py                  # RAG 지식 베이스
│   └── supabase_client.py      # Supabase DB 클라이언트
├── models/
│   ├── strategy.py             # 전략 데이터 모델
│   ├── backtest.py             # 백테스트 결과 모델
│   └── user.py                 # 사용자 모델
├── prompts/
│   ├── strategy_parser.py      # 전략 파싱 프롬프트
│   ├── coaching.py             # AI 코칭 프롬프트
│   └── backtest_report.py      # 백테스트 AI 분석 리포트 프롬프트
├── data/
│   └── example_strategies.py   # 예시 전략 템플릿
├── tests/
│   ├── conftest.py             # 테스트 설정
│   └── test_api.py             # API 테스트
├── requirements.txt
└── Dockerfile
```

### 3-3. API 엔드포인트

```
GET    /health                          # 서버 헬스체크

POST   /auth/wallet                     # nonce 요청 (rate limit: 10/min)
POST   /auth/verify                     # 서명 검증 → JWT 발급 (rate limit: 5/min)
GET    /auth/me                         # 현재 사용자 정보

POST   /chat/message                    # 채팅 메시지 전송 → AI 응답 (텍스트)
POST   /chat/message/image              # 이미지 포함 메시지 → AI 멀티모달 분석
POST   /chat/message/stream             # SSE 스트리밍 응답
GET    /chat/history/{strategy_id}      # 대화 히스토리 조회

POST   /strategy/parse                  # 자연어 → 구조화된 전략 JSON
POST   /strategy/save                   # 전략 저장
GET    /strategy/list                   # 내 전략 목록
GET    /strategy/{strategy_id}          # 전략 상세
POST   /strategy/fork/{strategy_id}     # 예시 전략 포크 (복사)
PUT    /strategy/{strategy_id}          # 전략 수정
DELETE /strategy/{strategy_id}          # 전략 삭제

POST   /backtest/run                    # 백테스트 실행
GET    /backtest/result/{backtest_id}   # 백테스트 결과 조회
GET    /backtest/history/{strategy_id}  # 전략별 백테스트 히스토리
DELETE /backtest/history/{backtest_id}  # 백테스트 기록 삭제
POST   /backtest/link                   # 백테스트 결과를 전략에 연결
POST   /backtest/analyze                # AI 백테스트 분석 리포트

GET    /market/prices                   # 주요 토큰 실시간 가격 (Jupiter)
GET    /market/price/{symbol}           # 단일 토큰 가격
```

---

## 4. 데이터 설계

### 4-1. DB 스키마 (Supabase PostgreSQL)

```sql
-- 사용자 (지갑 기반 인증)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address VARCHAR(44) UNIQUE NOT NULL,
  display_name VARCHAR(50),
  tier VARCHAR(10) DEFAULT 'free',  -- free | pro
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 전략
CREATE TABLE strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  raw_input TEXT NOT NULL,             -- 사용자 원본 입력 (자연어/전략 텍스트)
  input_type VARCHAR(10) DEFAULT 'text', -- text | image | paste (입력 유형)
  image_url TEXT,                      -- 이미지 입력 시 저장 URL (Supabase Storage)
  parsed_strategy JSONB NOT NULL,      -- AI가 파싱한 구조화 전략
  status VARCHAR(20) DEFAULT 'draft',  -- draft | tested | verified
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 백테스트 결과
CREATE TABLE backtest_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  -- 핵심 지표
  total_return DECIMAL(10,2),          -- 총 수익률 (%)
  max_drawdown DECIMAL(10,2),          -- 최대 낙폭 (%)
  sharpe_ratio DECIMAL(5,2),           -- 샤프 비율
  win_rate DECIMAL(5,2),               -- 승률 (%)
  total_trades INTEGER,                -- 총 거래 수
  -- 설정
  token_pair VARCHAR(20),              -- 예: SOL/USDC
  timeframe VARCHAR(10),               -- 예: 1h, 4h, 1d
  start_date DATE,
  end_date DATE,
  -- 상세 데이터
  equity_curve JSONB,                  -- 자산 곡선 [{date, value}]
  trade_log JSONB,                     -- 거래 내역 [{entry, exit, pnl}]
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 채팅 히스토리
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  role VARCHAR(10) NOT NULL,           -- user | assistant
  content TEXT NOT NULL,
  metadata JSONB,                      -- 전략 카드, 백테스트 참조 등
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4-2. 전략 JSON 스키마 (parsed_strategy)

Gemini가 자연어를 파싱하여 생성하는 구조화된 전략:

```json
{
  "name": "거래량 급증 전략",
  "version": 1,
  "entry": {
    "conditions": [
      {
        "indicator": "volume_change",
        "operator": ">=",
        "value": 300,
        "unit": "percent",
        "description": "거래량이 3배 이상 급증"
      }
    ],
    "logic": "AND"
  },
  "exit": {
    "take_profit": {
      "type": "percent",
      "value": 20,
      "partial": {
        "enabled": true,
        "at_percent": 20,
        "sell_ratio": 0.5
      }
    },
    "stop_loss": {
      "type": "percent",
      "value": -10
    }
  },
  "position": {
    "size_type": "fixed_usd",
    "size_value": 1000,
    "max_positions": 1
  },
  "filters": {
    "min_liquidity_usd": 50000,
    "min_market_cap_usd": 1000000,
    "exclude_tokens": [],
    "token_whitelist": []
  },
  "timeframe": "1h",
  "target_pair": "SOL/USDC"
}
```

---

## 5. AI 코칭 설계

### 5-1. Gemini 3.1 Pro 멀티모달 활용 (RAG 없이)

MVP에서는 RAG 파이프라인 대신 **직접 프롬프트 + few-shot examples**로 구현.
Gemini 3.1 Pro의 **멀티모달 기능**을 활용하여 3가지 입력을 모두 지원:

**입력 유형 (README 4-1 Strategy Builder 전체 구현):**

| 입력 방식 | 예시 | Gemini 처리 |
|-----------|------|------------|
| 자연어 텍스트 | "거래량 3배 터진 코인 소액 진입, 20% 익절" | 텍스트 → 전략 JSON 파싱 |
| 차트 이미지 | 캔들 차트 스크린샷 업로드 | 이미지 + 텍스트 → 패턴 인식 → 전략 JSON |
| 전략 텍스트 붙여넣기 | 다른 곳에서 본 전략 설명 복붙 | 텍스트 해석 → 구조화된 전략 JSON |

```
┌────────────────────────────────────────┐
│ 사용자 입력 (3가지 방식)                 │
│ A) 자연어: "거래량 3배 터진 코인..."     │
│ B) 이미지: 캔들 차트 스크린샷            │
│ C) 전략 텍스트: 복붙한 전략 설명         │
└──────────────┬─────────────────────────┘
               ▼
┌────────────────────────────────────────┐
│ System Prompt                          │
│ - 역할: 트레이딩 코치                    │
│ - 전략 파싱 규칙 (JSON 스키마 포함)       │
│ - 이미지 분석 가이드라인 (차트 패턴 인식)  │
│ - 코칭 가이드라인                        │
│ - Few-shot 예시 (3-5개)                 │
│ - 백테스트 결과 컨텍스트 (있을 경우)       │
└──────────────┬─────────────────────────┘
               ▼
┌────────────────────────────────────────┐
│ Gemini 3.1 Pro 응답                     │
│ - 구조화된 전략 JSON                     │
│ - 코칭 메시지 (리스크 분석 포함)          │
│ - 개선 제안                             │
│ - (이미지 시) 인식된 패턴 설명            │
└────────────────────────────────────────┘
```

**이미지 입력 처리 플로우:**
```python
# 백엔드: services/gemini.py
import google.generativeai as genai
from PIL import Image

async def parse_strategy_multimodal(text: str, image: bytes | None):
    model = genai.GenerativeModel("gemini-1.5-pro")

    parts = [SYSTEM_PROMPT]
    if image:
        img = Image.open(io.BytesIO(image))
        parts.append(img)
        parts.append("위 차트 이미지를 분석하여 트레이딩 전략으로 변환해주세요.")
    if text:
        parts.append(text)

    response = await model.generate_content_async(parts)
    return parse_strategy_json(response.text)
```

**프론트엔드 이미지 첨부 UX:**
- 파일 선택 버튼 (📎 아이콘)
- 드래그 & 드롭 지원
- 클립보드 붙여넣기 (Ctrl+V) 지원
- 첨부 시 미리보기 썸네일 표시, X 버튼으로 제거

### 5-2. AI 대화 플로우

```
1) 사용자: 자연어 전략 입력
   → AI: 전략 파싱 + 전략 카드 표시 + "백테스트 해볼까요?"

2) 사용자: "네, 해주세요" / 자동 실행
   → 시스템: 백테스트 실행 → 결과 차트 표시
   → AI: 결과 분석 코칭 (MDD, 승률, Sharpe 해석)

3) 사용자: "손절 라인을 좀 줄여줘"
   → AI: 전략 수정 → 재백테스트 → 비교 분석
   → AI: "손절을 -10%→-7%로 조정하면 MDD가 -45%→-28%로 개선됩니다"

4) 반복: 대화를 통한 전략 개선 루프
```

### 5-3. 전략 카드 UI (StrategyCard.tsx)

AI가 파싱한 전략 JSON을 시각적 카드로 렌더링:

```
┌─────────────────────────────────────────┐
│ 📊 거래량 급증 전략                v1    │
│─────────────────────────────────────────│
│ 진입 조건                               │
│ ├ 거래량 변화 ≥ 300%                    │
│ └ 로직: AND                             │
│─────────────────────────────────────────│
│ 익절        │ 손절        │ 투자금       │
│ +20% (절반) │ -10%       │ $1,000      │
│─────────────────────────────────────────│
│ 대상: SOL/USDC │ 타임프레임: 1h         │
│─────────────────────────────────────────│
│ [백테스트 실행] [전략 수정]              │
└─────────────────────────────────────────┘
```

카드에 표시하는 필드 (README 4-1 "출력" 항목 전체 반영):
- 진입 조건 (entry conditions)
- 투자금 (investment amount, 사용자 직접 입력 가능)
- 익절 규칙 (take profit)
- 손절 규칙 (stop loss)
- 대상 토큰 페어 + 타임프레임

> **참고**: 포지션 수(max_positions)는 항상 1로 고정. 투자금(size_value)이 곧 init_cash.

### 5-4. 프롬프트 설계 핵심

**System Prompt 구조:**
1. 역할 정의: "당신은 트레이딩 교육 전문 AI 코치입니다"
2. 규칙: 항상 리스크를 먼저 언급, 수익 보장 표현 금지
3. 전략 JSON 스키마: 파싱 출력 형식 명시
4. 코칭 톤: 교육적, 질문 유도, 대안 제시
5. Few-shot: 3가지 전략 유형별 파싱 예시

---

## 6. 백테스트 엔진 설계

### 6-1. 엔진 구조

```
parsed_strategy (JSON)
        ↓
┌───────────────────────┐
│ 데이터 수집            │ Binance REST API
│ OHLCV + Volume        │ → pandas DataFrame 캐싱
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ VectorBT 백테스트     │
│ - 진입/퇴장 시그널 생성 │
│ - 포지션 사이즈 적용    │
│ - 수수료 0.04% 반영    │
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ 결과 산출              │
│ - total_return         │
│ - max_drawdown         │
│ - sharpe_ratio         │
│ - win_rate             │
│ - equity_curve         │
│ - trade_log            │
└───────────────────────┘
```

### 6-2. 데이터 수집 전략

Binance API를 통해 **실시간 OHLCV 데이터**를 수집:

```python
# 주요 페어 (Binance 심볼 매핑)
SUPPORTED_PAIRS = [
    "SOL/USDC",   # Solana 기본 → SOLUSDC
    "BTC/USDT",   # 비트코인 → BTCUSDT
    "ETH/USDT",   # 이더리움 → ETHUSDT
]

# Binance Klines API (무료, API 키 불필요)
# GET /api/v3/klines?symbol=SOLUSDC&interval=1h&limit=1000
# 최근 30일~1000봉 데이터 수집 → pandas DataFrame
# 실시간 가격: Jupiter Quote API (Solana 토큰용)
```

### 6-3. 지표 계산

| 지표 | 계산 방식 | MVP 기준값 |
|------|----------|-----------|
| 총 수익률 | (최종자산 - 초기자산) / 초기자산 * 100 | - |
| MDD | 자산 곡선의 고점 대비 최대 하락폭 | 경고: -30% 초과 시 |
| Sharpe Ratio | (평균수익률 - 무위험수익률) / 표준편차 | 양호: > 1.0 |
| 승률 | 수익 거래 / 전체 거래 * 100 | 참고용 |

---

## 7. 인증 설계 (지갑 기반)

### 7-1. Phantom 지갑 인증 플로우

```
1) 프론트엔드: Phantom 지갑 연결 요청
2) 사용자: Phantom에서 연결 승인
3) 프론트엔드: wallet.publicKey 획득
4) 프론트엔드 → 백엔드: POST /auth/wallet { wallet_address }
5) 백엔드: nonce 생성 → 반환 (rate limit: 10/min)
6) 프론트엔드: nonce를 Phantom으로 서명 요청
7) 사용자: 서명 승인
8) 프론트엔드 → 백엔드: POST /auth/verify { wallet_address, signature, nonce } (rate limit: 5/min)
9) 백엔드: 서명 검증 → JWT 토큰 발급
10) 이후 모든 API 호출에 JWT 포함
```

### 7-2. 미인증 사용 (Free Tier)

- 지갑 연결 없이도 채팅 + 백테스트 3회 가능 (localStorage 기반 카운트)
- 지갑 연결 시 전략 저장, 히스토리 영구 보존

---

## 8. 환경변수

```env
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=https://api.tradecoach.ai  # Railway 백엔드 URL
NEXT_PUBLIC_SOLANA_RPC=https://mainnet.helius-rpc.com/?api-key=xxx
NEXT_PUBLIC_SOLANA_NETWORK=mainnet-beta

# Backend (.env)
GEMINI_API_KEY=xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx
JWT_SECRET=xxx
CORS_ORIGINS=https://tradecoach.ai,http://localhost:3000
```

---

## 9. 7일 MVP 구현 계획

### Day-by-Day 일정

| Day | 작업 | 산출물 | 담당 |
|-----|------|--------|------|
| **D1** | 프로젝트 스캐폴딩 | Next.js + FastAPI + Supabase 초기 설정, DB 마이그레이션 | 서훈 |
| **D2** | 랜딩 페이지 | pencil 디자인 → 코드 변환 (10개 섹션) | 서훈 |
| **D3** | 채팅 UI + Gemini 멀티모달 연동 | 채팅 UI (텍스트+이미지 입력), Gemini 멀티모달 API, 전략 파싱 프롬프트, 전략 카드 렌더링 | 서훈 |
| **D4** | 백테스트 엔진 | VectorBT 백테스트, Binance 데이터 수집, 결과 저장 | 서훈+인희 |
| **D5** | 백테스트 시각화 + AI 코칭 | 차트 렌더링, 코칭 대화 루프, 전략 수정 재백테스트 | 서훈+인희 |
| **D6** | 지갑 연동 + 전략 저장 | Phantom 인증, 전략 CRUD, 대화 히스토리 | 서훈 |
| **D7** | 통합 테스트 + 배포 + 데모 | Vercel/Railway 배포, 시연 시나리오 준비 | 전원 |

### MVP 범위 (README Phase 1 기준)

**반드시 구현 (README Phase 1 전체 반영):**
- [x] 채팅 기반 전략 빌더 UI (자연어 입력)
- [x] Gemini 3.1 Pro 연동 전략 파싱
- [x] 백테스트 결과 표시 + AI 코칭 대화
- [x] 솔라나 지갑 연동 (Phantom)
- [x] 이미지 입력 (차트 캡처 → Gemini 멀티모달 전략 변환)
- [x] 전략 카드 시각화 (진입조건, 포지션, 익절, 손절, 필터 표시)
- [x] 전략 텍스트 붙여넣기 (다른 곳에서 본 전략 해석)

**Post-MVP로 확실히 제외:**
- RAG 파이프라인 (LlamaIndex)
- 최적화 + Walk-Forward Analysis
- 모의투자 WebSocket
- 전략 마켓플레이스 / 카피트레이딩
- cNFT 민팅

---

## 10. 디자인 시스템 (pencil 기반)

### 색상 팔레트

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--bg-primary` | `#0A0F1C` | 메인 배경 |
| `--bg-secondary` | `#0F172A` | 섹션 배경 |
| `--bg-card` | `#1E293B` | 카드 배경 |
| `--accent` | `#22D3EE` | 시안 포인트 (CTA, 링크, 뱃지) |
| `--accent-dark` | `#0891B2` | 시안 그라디언트 끝 |
| `--text-primary` | `#FFFFFF` | 헤드라인 |
| `--text-secondary` | `#94A3B8` | 본문, 설명 |
| `--text-muted` | `#475569` | 보조 텍스트 |
| `--text-footer` | `#64748B` | 푸터 |
| `--border` | `#22D3EE33` | 카드 테두리 (반투명 시안) |
| `--border-subtle` | `#47556933` | 입력 필드 테두리 |

### 타이포그래피

| 용도 | 폰트 | 사이즈 | Weight |
|------|------|--------|--------|
| 헤드라인 | Inter | 64px / 40px | Bold |
| 서브헤드 | Inter | 18px | Normal |
| 본문 | Inter | 14-16px | Normal/500 |
| 코드/뱃지 | JetBrains Mono | 12px | 500/Bold |
| 통계 수치 | JetBrains Mono | 36px | Bold |

### 컴포넌트 스타일

```css
/* CTA 버튼 (시안 그라디언트) */
.btn-primary {
  background: linear-gradient(90deg, #22D3EE, #06B6D4);
  border-radius: 8px;
  padding: 16px 32px;
  color: #0A0F1C;
  font-weight: 600;
}

/* 카드 */
.card {
  background: #1E293B;
  border-radius: 12px;
  padding: 28-32px;
  border: 1px solid #22D3EE33; /* 선택적 */
}

/* 네비게이션 */
.nav {
  background: #0A0F1CCC; /* 80% 불투명 */
  height: 80px;
  padding: 0 120px;
}
```

---

## 11. 핵심 데이터 플로우

### 전략 생성 → 백테스트 → 코칭 루프

```
사용자 입력: "거래량 3배 터진 코인 소액 진입, 20% 익절"
    │
    ├─ POST /chat/message { content, strategyId? }
    │
    ▼
Backend: gemini.parse_strategy(user_input)
    │
    ├─ 전략 JSON 생성 → DB 저장
    ├─ AI 응답: "전략을 분석했습니다. [전략 카드] 백테스트 해볼까요?"
    │
    ▼
사용자: "네"
    │
    ├─ POST /backtest/run { strategyId }
    │
    ▼
Backend: backtest_engine.run(strategy, ohlcv_data)
    │
    ├─ VectorBT 실행 → 결과 DB 저장
    ├─ gemini.coaching(strategy, backtest_result)
    ├─ AI 응답: "MDD -67%는 위험합니다. [차트] 손절 라인 조정 제안..."
    │
    ▼
사용자: "손절 -30%로 줄여줘"
    │
    ├─ POST /chat/message { content, strategyId }
    │
    ▼
Backend: gemini.modify_strategy(current_strategy, user_request)
    │
    ├─ 전략 수정 → 재백테스트 → 비교 결과
    ├─ AI 응답: "MDD -67%→-28%로 개선. Sharpe도 0.8→1.2로 상승!"
    │
    ▼
(반복)
```

---

## 12. 리스크 및 제약사항

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Binance API 호출 제한 | 백테스트 데이터 부족 | 무료 API, 1000봉 단위 수집 |
| Gemini API 지연 | 채팅 응답 느림 | 스트리밍 응답, 로딩 UI |
| Vercel 서버리스 한계 | WebSocket 불가 | MVP는 REST 폴링, Post-MVP에서 Railway WS |
| VectorBT 학습 곡선 | 개발 지연 | 인희님 자문 + 간단한 전략부터 |
| 무료 티어 남용 | 비용 초과 | localStorage 카운트 + rate limiting |

---

> **다음 단계**: 이 설계서를 기반으로 Day 1 프로젝트 스캐폴딩 시작
> **UI 구현**: pencil-new.pen 디자인을 Tailwind 코드로 변환

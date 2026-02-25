# TradeCoach AI 사용 가이드

> 이 문서는 TradeCoach AI 프로젝트를 로컬 환경에서 실행하고 사용하는 방법을 안내합니다.

---

## 목차

1. [사전 준비](#1-사전-준비)
2. [API 키 발급](#2-api-키-발급)
3. [백엔드 설정 및 실행](#3-백엔드-설정-및-실행)
4. [프론트엔드 설정 및 실행](#4-프론트엔드-설정-및-실행)
5. [주요 기능 사용법](#5-주요-기능-사용법)
6. [API 레퍼런스](#6-api-레퍼런스)
7. [데이터베이스 스키마](#7-데이터베이스-스키마)
8. [배포 가이드](#8-배포-가이드)
9. [MVP 제한 사항](#9-mvp-제한-사항)
10. [문제 해결](#10-문제-해결)

---

## 1. 사전 준비

### 필수 소프트웨어

| 소프트웨어 | 최소 버전 | 용도 |
|-----------|----------|------|
| Python | 3.11+ | 백엔드 서버 |
| Node.js | 18+ | 프론트엔드 빌드 |
| npm | 9+ | 패키지 관리 |
| Git | 2.30+ | 소스 코드 관리 |

### 선택 사항

| 소프트웨어 | 용도 |
|-----------|------|
| Docker | 컨테이너 기반 배포 |
| Phantom Wallet | 솔라나 지갑 연동 (브라우저 확장) |

---

## 2. API 키 발급

TradeCoach AI를 완전하게 사용하려면 다음 API 키가 필요합니다.

### 필수 키

| API 키 | 발급처 | 용도 |
|--------|-------|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) | AI 전략 파싱 및 코칭 |
| `BIRDEYE_API_KEY` | [Birdeye](https://birdeye.so/) | 솔라나 DEX OHLCV 데이터 |

### 선택 키

| API 키 | 발급처 | 용도 |
|--------|-------|------|
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | [Supabase](https://supabase.com/) | 데이터베이스 (없으면 MVP 모드로 동작) |
| `NEXT_PUBLIC_SOLANA_RPC` | [Helius](https://helius.dev/) | 솔라나 RPC 노드 |

> **참고**: Supabase 키가 없어도 MVP 모드로 동작합니다. 전략 파싱, AI 코칭, 백테스트 등 핵심 기능은 정상 작동하며, 데이터 영구 저장만 비활성화됩니다.

---

## 3. 백엔드 설정 및 실행

### 3-1. 환경 변수 설정

```bash
cd backend
cp .env.example .env
```

`.env` 파일을 열어 API 키를 입력합니다:

```env
GEMINI_API_KEY=your-gemini-api-key
BIRDEYE_API_KEY=your-birdeye-api-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-key
JWT_SECRET=your-jwt-secret-change-me
CORS_ORIGINS=http://localhost:3000
```

### 3-2. Python 가상환경 생성 및 의존성 설치

```bash
# 가상환경 생성
python -m venv venv

# 활성화 (macOS/Linux)
source venv/bin/activate

# 활성화 (Windows)
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

> **주의**: `vectorbt==0.26.2`는 `plotly<6`을 요구합니다. `plotly 6.x`가 설치되면 호환성 에러가 발생할 수 있습니다.

### 3-3. 서버 실행

```bash
# 개발 모드 (핫 리로드)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

서버가 정상 실행되면:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 3-4. 헬스 체크

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

### 3-5. API 문서 확인

FastAPI가 자동 생성하는 API 문서를 브라우저에서 확인할 수 있습니다:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 4. 프론트엔드 설정 및 실행

### 4-1. 환경 변수 설정

```bash
cd frontend
cp .env.local.example .env.local
```

`.env.local` 파일을 열어 설정합니다:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SOLANA_RPC=https://mainnet.helius-rpc.com/?api-key=xxx
NEXT_PUBLIC_SOLANA_NETWORK=mainnet-beta
```

### 4-2. 의존성 설치 및 실행

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

브라우저에서 http://localhost:3000 으로 접속합니다.

### 4-3. 프로덕션 빌드

```bash
npm run build
npm start
```

---

## 5. 주요 기능 사용법

### 5-1. 전략 생성 (Strategy Builder)

1. http://localhost:3000/chat 에 접속
2. 채팅 입력창에 자연어로 트레이딩 전략을 입력합니다

**입력 예시**:
```
RSI 30 이하에서 매수, 70 이상에서 매도
```
```
거래량이 갑자기 3배 이상 늘어난 토큰을 발견하면 소액 진입, 20% 수익 시 절반 익절
```

3. Gemini 3.1 Pro가 입력을 분석하여 **전략 카드**를 생성합니다
   - 진입 조건 (Entry Conditions)
   - 익절/손절 라인 (Take Profit / Stop Loss)
   - 포지션 사이즈 (Position Size)
   - 대상 페어 (Token Pair)
   - 타임프레임 (Timeframe)

### 5-2. 이미지 입력 (차트 분석)

1. 채팅 입력창 왼쪽의 이미지 버튼을 클릭하거나, 이미지를 클립보드에서 붙여넣기
2. 캔들 차트 캡처를 업로드하면 AI가 패턴을 분석하여 전략으로 변환
3. 최대 10MB까지 지원 (PNG, JPG, WEBP)

### 5-3. AI 코칭

전략 카드가 생성된 후 추가 대화를 통해 AI 코칭을 받을 수 있습니다:

```
이 전략으로 백테스트 해줘
```
```
손절 라인을 -30%로 수정하면 어떨까?
```
```
횡보장에서도 잘 작동하게 조건 추가해줘
```

AI 코치는 리스크 분석과 개선점을 제안하며, 사용자와 대화하면서 전략을 반복적으로 발전시킵니다.

### 5-4. 백테스트

전략 카드의 데이터를 바탕으로 솔라나 DEX 과거 데이터에 대해 백테스트를 실행합니다:

- **지원 토큰 페어**: SOL/USDC (기본), 주요 솔라나 토큰
- **데이터 소스**: Birdeye API (OHLCV)
- **결과 지표**: 총 수익률, 최대 낙폭(MDD), 샤프 비율, 승률, 총 거래 횟수
- **시각화**: 자산 곡선 (Equity Curve), 거래 로그

### 5-5. 지갑 연동

1. Phantom Wallet 브라우저 확장을 설치
2. 랜딩 페이지 우측 상단의 "지갑 연결" 버튼 클릭
3. Phantom이 연결 요청을 표시하면 승인
4. 지갑 주소 기반으로 사용자 계정이 자동 생성됩니다

---

## 6. API 레퍼런스

### 인증 (Auth)

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/auth/wallet` | 지갑 주소로 nonce 요청 |
| `POST` | `/auth/verify` | 서명 검증 후 JWT 발급 |
| `GET` | `/auth/me` | 현재 사용자 정보 조회 |

**POST /auth/wallet**
```json
// Request
{ "wallet_address": "AbCd...1234" }

// Response
{ "nonce": "a1b2c3d4..." }
```

**POST /auth/verify**
```json
// Request
{
  "wallet_address": "AbCd...1234",
  "signature": "base58-encoded-signature",
  "nonce": "a1b2c3d4..."
}

// Response
{
  "access_token": "eyJ...",
  "user": {
    "id": "uuid",
    "wallet_address": "AbCd...1234",
    "display_name": null,
    "tier": "free",
    "created_at": "2026-02-25T..."
  }
}
```

### 채팅 (Chat)

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/chat/message` | 텍스트 메시지 전송 (Form) |
| `POST` | `/chat/message/image` | 이미지 포함 메시지 전송 (Multipart) |
| `GET` | `/chat/history/{strategy_id}` | 대화 히스토리 조회 |

**POST /chat/message**
```bash
# Content-Type: multipart/form-data
curl -X POST http://localhost:8000/chat/message \
  -F "content=RSI 30 이하에서 매수, 70 이상에서 매도" \
  -F "strategy_id=optional-id"
```
```json
// Response
{
  "type": "strategy_parsed",
  "message": "AI 코칭 응답 텍스트",
  "parsed_strategy": { ... }
}
```

**POST /chat/message/image**
```bash
curl -X POST http://localhost:8000/chat/message/image \
  -F "content=이 차트 패턴 분석해줘" \
  -F "image=@chart.png" \
  -F "strategy_id=optional-id"
```

### 전략 (Strategy)

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/strategy/parse` | 자연어 → 구조화된 전략 JSON |
| `GET` | `/strategy/list` | 전략 목록 조회 |
| `GET` | `/strategy/{id}` | 전략 상세 조회 |
| `PUT` | `/strategy/{id}` | 전략 수정 |
| `DELETE` | `/strategy/{id}` | 전략 삭제 |

**POST /strategy/parse**
```json
// Request
{
  "raw_input": "RSI 30 이하에서 매수, 70 이상에서 매도",
  "input_type": "text"
}

// Response
{
  "parsed_strategy": {
    "entry": {
      "conditions": [
        { "indicator": "RSI", "operator": "<=", "value": 30 }
      ]
    },
    "exit": {
      "take_profit": { "type": "percentage", "value": 20 },
      "stop_loss": { "type": "percentage", "value": -10 }
    },
    "position": { "size": "5%", "max_positions": 1 },
    "pair": "SOL/USDC",
    "timeframe": "1h"
  }
}
```

### 백테스트 (Backtest)

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/backtest/run` | 백테스트 실행 |
| `GET` | `/backtest/result/{id}` | 백테스트 결과 조회 |

**POST /backtest/run**
```json
// Request
{
  "strategy_id": "local",
  "token_pair": "SOL/USDC",
  "timeframe": "1h",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "parsed_strategy": {
    "entry": { "conditions": [...] },
    "exit": { "take_profit": {...}, "stop_loss": {...} }
  }
}

// Response
{
  "id": "uuid",
  "metrics": {
    "total_return": 45.23,
    "max_drawdown": -18.5,
    "sharpe_ratio": 1.42,
    "win_rate": 62.5,
    "total_trades": 24
  },
  "equity_curve": [
    { "date": "2025-01-01", "value": 1000.0 },
    ...
  ],
  "trade_log": [
    {
      "entry_date": "2025-01-15",
      "exit_date": "2025-01-20",
      "pnl": 52.30,
      "return_pct": 5.23
    },
    ...
  ]
}
```

### 헬스 체크

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET` | `/health` | 서버 상태 확인 |

---

## 7. 데이터베이스 스키마

Supabase PostgreSQL을 사용합니다. MVP 모드에서는 DB 없이도 동작합니다.

### users 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | uuid (PK) | 사용자 고유 ID |
| `wallet_address` | varchar (UNIQUE) | 솔라나 지갑 주소 |
| `display_name` | varchar | 표시 이름 |
| `tier` | varchar | 구독 등급 (free/premium) |
| `created_at` | timestamptz | 가입일 |

### strategies 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | uuid (PK) | 전략 고유 ID |
| `user_id` | uuid (FK → users) | 소유자 |
| `raw_input` | text | 원본 입력 텍스트 |
| `input_type` | varchar | 입력 유형 (text/image) |
| `parsed_strategy` | jsonb | 파싱된 전략 JSON |
| `created_at` | timestamptz | 생성일 |
| `updated_at` | timestamptz | 수정일 |

### backtest_results 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | uuid (PK) | 백테스트 고유 ID |
| `strategy_id` | uuid (FK → strategies) | 전략 ID |
| `total_return` | float | 총 수익률 (%) |
| `max_drawdown` | float | 최대 낙폭 (%) |
| `sharpe_ratio` | float | 샤프 비율 |
| `win_rate` | float | 승률 (%) |
| `total_trades` | integer | 총 거래 수 |
| `token_pair` | varchar | 토큰 페어 |
| `timeframe` | varchar | 타임프레임 |
| `equity_curve` | jsonb | 자산 곡선 데이터 |
| `trade_log` | jsonb | 거래 로그 |
| `created_at` | timestamptz | 생성일 |

### chat_messages 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | uuid (PK) | 메시지 고유 ID |
| `strategy_id` | uuid (FK → strategies) | 관련 전략 |
| `role` | varchar | 발신자 (user/assistant) |
| `content` | text | 메시지 내용 |
| `metadata` | jsonb | 추가 데이터 |
| `created_at` | timestamptz | 생성일 |

---

## 8. 배포 가이드

### 프론트엔드 → Vercel

```bash
cd frontend
npx vercel
```

환경 변수를 Vercel 대시보드에서 설정:
- `NEXT_PUBLIC_API_URL` = 백엔드 배포 URL
- `NEXT_PUBLIC_SOLANA_RPC` = Helius RPC URL
- `NEXT_PUBLIC_SOLANA_NETWORK` = `mainnet-beta`

### 백엔드 → Railway

1. Railway 프로젝트 생성
2. GitHub 레포 연결
3. 환경 변수 설정 (`.env`와 동일)
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 데이터베이스 → Supabase

1. [Supabase](https://supabase.com/) 프로젝트 생성
2. SQL Editor에서 스키마 생성 (위 테이블 구조 참조)
3. Project URL과 Service Key를 환경 변수에 설정

---

## 9. MVP 제한 사항

현재 MVP 버전에서의 제한 사항입니다:

| 항목 | 제한 | 향후 계획 |
|------|------|----------|
| 지갑 서명 검증 | nonce 매칭만 (실제 서명 검증 미구현) | nacl.sign 검증 추가 |
| 지원 토큰 | 주요 솔라나 토큰만 | 전체 DEX 토큰 확장 |
| 백테스트 시그널 | 단순 지표 기반 (RSI, MA, Volume) | 복합 전략 지원 |
| 데이터 저장 | Supabase 없이 인메모리 | Supabase 완전 연동 |
| 모의투자 | 미구현 | Phase 2에서 추가 |
| 전략 마켓플레이스 | 미구현 | Phase 2에서 추가 |
| 실제 트레이딩 | 미구현 | Jupiter API 연동 예정 |
| RAG 연동 | 미구현 | 트레이딩 지식 베이스 구축 예정 |

---

## 10. 문제 해결

### "Supabase 연결 실패 (MVP 모드로 계속)" 로그

정상 동작입니다. Supabase 키가 없거나 유효하지 않으면 자동으로 MVP 모드로 전환됩니다. 핵심 기능은 모두 정상 작동합니다.

### Gemini API 응답이 느린 경우

Gemini 3.1 Pro Preview 모델은 응답에 10~30초가 걸릴 수 있습니다. 특히 전략 파싱 시 구조화된 JSON을 생성하는 데 시간이 소요됩니다.

### VectorBT 설치 오류

```bash
# plotly 버전 충돌 시
pip install "plotly<6"
pip install vectorbt==0.26.2
```

### 프론트엔드 빌드 오류

```bash
# node_modules 삭제 후 재설치
rm -rf node_modules .next
npm install
npm run build
```

### CORS 에러

백엔드 `.env`의 `CORS_ORIGINS`에 프론트엔드 URL이 포함되어 있는지 확인:
```env
CORS_ORIGINS=http://localhost:3000
```

여러 오리진이 필요한 경우 콤마로 구분:
```env
CORS_ORIGINS=http://localhost:3000,https://your-domain.vercel.app
```

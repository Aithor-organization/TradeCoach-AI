# TradeCoach-AI — 프로덕션 통합 구현계획서 v2.0

> 작성일: 2026-03-20
> 목표: MVP → Production-Grade 전환
> 기반: PROJECT_COMPARISON.md + STRATEGY-VAULT-DESIGN.md + SYSTEM_SPECIFICATION.md + 코드 버그 분석

---

## 목차

1. [현재 상태 요약](#1-현재-상태-요약)
2. [프로덕션 목표 아키텍처](#2-프로덕션-목표-아키텍처)
3. [Phase 0: 긴급 버그 수정](#3-phase-0-긴급-버그-수정)
4. [Phase 1: 보안 강화](#4-phase-1-보안-강화)
5. [Phase 2: 백테스트 엔진 프로덕션화](#5-phase-2-백테스트-엔진-프로덕션화)
6. [Phase 3: 실시간 트레이딩 고도화](#6-phase-3-실시간-트레이딩-고도화)
7. [Phase 4: 블록체인 실제 연동](#7-phase-4-블록체인-실제-연동)
8. [Phase 5: AI 엔진 고도화](#8-phase-5-ai-엔진-고도화)
9. [Phase 6: 마켓플레이스 + 수익화](#9-phase-6-마켓플레이스--수익화)
10. [Phase 7: 인프라 + 배포](#10-phase-7-인프라--배포)
11. [DB 스키마 확장](#11-db-스키마-확장)
12. [API 엔드포인트 전체 목록](#12-api-엔드포인트-전체-목록)
13. [테스트 전략](#13-테스트-전략)
14. [실행 타임라인](#14-실행-타임라인)

---

## 1. 현재 상태 요약

### 완료된 기능 (MVP)
- [x] AI 전략 생성 (Gemini 3.1 Pro, 텍스트 + 이미지)
- [x] 백테스트 엔진 (Futures, 레버리지 1-125x)
- [x] 파라미터 최적화 (Grid Search, 병렬)
- [x] 모의투자 (Binance REST 폴링 3초)
- [x] cNFT 민팅 프레임워크 (메타데이터 준비)
- [x] Phantom 지갑 + JWT 인증
- [x] AI 코칭 (coaching.py 프롬프트)
- [x] RAG 지식 베이스 (ChromaDB)

### 발견된 Critical 문제 (20건)
- 인증 서명 미검증 (누구나 지갑 도용 가능)
- 블록체인 TX 미전송 (로컬 해시만 계산)
- 세션 유저 격리 없음 (타인 세션 접근 가능)
- 메모리 누수 (세션 미정리)
- 백테스트 슬리피지 방향 반전
- 커미션 이중 차감
- klines 경쟁 상태
- 등 13건 추가

---

## 2. 프로덕션 목표 아키텍처

```
┌─────────────────── Frontend (Next.js 15 + Vercel) ──────────────────┐
│  Landing | Chat (AI Coach) | Strategies | Trading | Marketplace     │
│  + Phantom Wallet + lightweight-charts (WebSocket) + Zustand        │
└───────────────────────┬─────────────────────────────────────────────┘
                        │ REST + WebSocket (wss://)
┌───────────────────────┴─────────────────────────────────────────────┐
│              API Gateway (FastAPI + Uvicorn)                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐          │
│  │ Auth     │ Chat     │ Strategy │ Backtest │ Trading  │          │
│  │ (nacl)   │ (Gemini) │ (CRUD)   │ (Celery) │ (WS)    │          │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘          │
│  ┌──────────┬──────────┬──────────┬──────────┐                     │
│  │ Optimize │ Market   │ Blockchain│ Dispatch │                     │
│  │ (Grid)   │ (Jupiter)│ (Solana) │ (Multi)  │                     │
│  └──────────┴──────────┴──────────┴──────────┘                     │
│                                                                     │
│  Background Workers:                                                │
│  ├─ Celery (백테스트 + IS/OOS + Walk-Forward)                       │
│  ├─ Price Feed (Binance WebSocket aggTrade)                         │
│  └─ Signal Dispatcher (Webhook + Telegram + Discord + Solana)       │
│                                                                     │
│  Data Layer:                                                        │
│  ├─ PostgreSQL (Supabase) — 사용자, 전략, 거래, 세션               │
│  ├─ Redis — 세션 캐시, Celery 큐, Rate Limit                       │
│  ├─ ChromaDB — RAG 벡터 지식 베이스                                │
│  └─ Binance Futures API — OHLCV, WebSocket                         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────────┐
│                    Solana Blockchain (devnet → mainnet)              │
│  ├─ Strategy cNFT (Metaplex Bubblegum)                              │
│  ├─ Signal Recording (SPL Account Compression)                      │
│  ├─ Pyth Oracle 이중 가격 검증                                      │
│  ├─ Performance Verification (독립 검증)                             │
│  └─ Marketplace Escrow (구매 + 렌탈)                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 0: 긴급 버그 수정 (1-2일)

> 프로덕션 배포 전 반드시 해결해야 하는 즉각적인 문제들.

### 0.1 세션 유저 격리
**파일**: `backend/routers/trading.py`
```
변경: demo_status, demo_history 엔드포인트에서 user_id == session.user_id 검증
영향: 4개 엔드포인트 (status, history, stop, start)
```

### 0.2 메모리 누수 수정
**파일**: `backend/routers/trading.py`, `backend/services/demo_price_feed.py`
```
변경:
- start_demo에 try/except 감싸기 (task 생성 실패 시 세션 정리)
- run_price_feed에 최대 실행 시간 (24시간) + API 실패 시 30초 후 세션 자동 종료
- 서버 시작 시 stale 세션 정리 로직
```

### 0.3 백테스트 슬리피지 방향 수정
**파일**: `backend/services/futures/engine.py:198-200`
```python
# 수정 전
return price + tick if side == "long" else price - tick
# 수정 후: 진입 시 불리한 방향으로
# LONG 진입: 높은 가격에 삼 (+tick)
# SHORT 진입: 낮은 가격에 숏 (-tick) → 불리하려면 높은 가격이어야 함
return price + tick  # 진입은 항상 불리한 방향
# 퇴장 슬리피지도 추가 (반대 방향)
```

### 0.4 커미션 이중 차감 수정
**파일**: `backend/services/demo_trading.py:256-259`
```
변경: close_position에서 commission 한 곳에서만 차감
```

### 0.5 Sharpe/Profit Factor 방어 코드
**파일**: `backend/services/futures/metrics.py`
```
변경:
- len(returns) == 0 체크 추가 (Sharpe)
- profit_factor = min(pf, 999.99) 캡핑 (JSON 직렬화 안전)
- losses 분류: pnl < 0 (== 0은 breakeven 별도)
```

### 0.6 klines 경쟁 상태 수정
**파일**: `backend/services/demo_price_feed.py:113-116`
```
변경: klines 수정 시 copy.deepcopy() 사용하여 원본 보호
```

---

## 4. Phase 1: 보안 강화 (3-5일)

> 프로덕션 배포의 최소 보안 요구사항.

### 1.1 Solana 서명 검증 구현
**파일**: `backend/routers/auth.py`
```python
# nacl 패키지 설치: pip install pynacl
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import base58

def verify_solana_signature(message: str, signature: str, public_key: str) -> bool:
    try:
        verify_key = VerifyKey(base58.b58decode(public_key))
        signature_bytes = base58.b58decode(signature)
        verify_key.verify(message.encode(), signature_bytes)
        return True
    except (BadSignatureError, Exception):
        return False
```
**의존성 추가**: `pynacl>=1.5.0`, `base58>=2.1.0`

### 1.2 JWT 페이로드 통일 + 만료 수정
**파일**: `backend/routers/auth.py`, `backend/dependencies.py`
```
변경:
- exp를 int(datetime.timestamp())로 변환 (Unix timestamp)
- 모든 JWT에 동일 구조: {"sub": user_id, "iat": now, "exp": expire}
- dependencies.py에 명시적 만료 검증 추가
```

### 1.3 이메일 인증 플로우 추가
**파일**: `backend/routers/auth.py` (신규 엔드포인트)
```
POST /auth/send-verification — 인증 코드 이메일 발송
POST /auth/verify-email — 코드 확인 + 계정 활성화
의존성: Supabase Auth 또는 Resend/SendGrid API
```

### 1.4 Rate Limiting 강화
**파일**: `backend/main.py`
```
변경:
- IP + User 복합 키: key_func = lambda req: f"{get_remote_address(req)}:{get_user_id(req)}"
- 엔드포인트별 세분화:
  - 인증: 5/min (IP)
  - 채팅: 30/min (User)
  - 백테스트: 10/min (User)
  - 최적화: 5/min (User)
  - 트레이딩: 20/min (User)
```

### 1.5 Helius API 키 보안
**파일**: `backend/services/blockchain/solana_client.py`
```
변경: URL 파라미터 → Authorization 헤더로 이동
- 모든 httpx 호출에 headers={"Authorization": f"Bearer {HELIUS_API_KEY}"} 추가
- Helius API 에러 핸들링 (status code + error field 체크)
- 타임아웃: 10초
```

### 1.6 입력 검증 강화
**파일**: 모든 라우터, `signal_recorder.py`
```
변경:
- Pydantic 모델에 Field(ge=0, le=125) 등 범위 검증
- leverage: 1-125 정수
- price: > 0
- symbol: 알파벳+숫자 20자 이내
- wallet_address: base58 44자
```

---

## 5. Phase 2: 백테스트 엔진 프로덕션화 (5-7일)

### 2.1 슬리피지 시뮬레이션 완성
**파일**: `backend/services/futures/engine.py`, `types.py`
```
변경:
- FuturesConfig에 slippage_pct: float = 0.01 추가
- 진입 + 퇴장 모두 슬리피지 적용
- LONG 진입: price * (1 + slippage), LONG 퇴장: price * (1 - slippage)
- SHORT 진입: price * (1 - slippage), SHORT 퇴장: price * (1 + slippage)
```

### 2.2 청산가격 로직 정상화
**파일**: `backend/services/futures/types.py:96-97`
```
변경:
- 하드코딩 0.006 제거
- Binance 유지증거금 비율 테이블 적용:
  | 레버리지 | 유지증거금 |
  |---------|----------|
  | 1-10x   | 0.50%    |
  | 11-20x  | 1.00%    |
  | 21-50x  | 2.50%    |
  | 51-125x | 5.00%    |
- liquidation_price = entry * (1 - (initial_margin - maintenance_margin) / entry_value)
```

### 2.3 IS/OOS 과적합 검증 통합
**파일**: `backend/services/futures/isoos_runner.py` (신규)
```python
class ISOOSRunner:
    def run(self, strategy, bars, config) -> ISOOSResult:
        # 데이터 분할: 2/3 IS + 1/3 OOS
        split_idx = len(bars) * 2 // 3
        is_bars = bars[:split_idx]
        oos_bars = bars[split_idx:]

        # 각각 백테스트 실행
        is_result = FuturesBacktestEngine(config).run(is_bars, strategy)
        oos_result = FuturesBacktestEngine(config).run(oos_bars, strategy)
        full_result = FuturesBacktestEngine(config).run(bars, strategy)

        # 과적합 점수
        oos_is_ratio = oos_result.total_return / is_result.total_return if is_result.total_return != 0 else 0
        overfitting_score = max(0, 1 - oos_is_ratio)

        # 판정
        if oos_is_ratio >= 0.5: recommendation = "SAFE"
        elif oos_is_ratio >= 0.25: recommendation = "CAUTIOUS"
        elif oos_is_ratio >= 0.1: recommendation = "RISKY"
        else: recommendation = "REJECT"

        return ISOOSResult(is_result, oos_result, full_result, overfitting_score, recommendation)
```
**라우터**: `POST /backtest/isoos` 엔드포인트 추가

### 2.4 CAGR 메트릭 정상화
**파일**: `backend/services/futures/metrics.py`
```
변경:
- 36.5일 미만: CAGR = None (0이 아님)
- JSON 출력 시 null로 표시
- 프론트엔드에서 "N/A (기간 부족)" 표시
```

### 2.5 기술 지표 25개 추가 (12 → 37+개) + DDIF/MADDIF 전략 지표
**파일**: `backend/services/futures/indicators_extended.py` (신규)
```
추가 지표 (BinanceTrader 참조):
- 추세: ADX, DI_PLUS, DI_MINUS, SAR, AROON_UP, AROON_DOWN
- 모멘텀: CCI, MOM, ROC, WILLR, MFI, APO, PPO
- 거래량: OBV, AD, ADOSC
- 추가 이동평균: EMA_60, EMA_120, SMA_60

RCoinFutTrader 핵심 전략 지표 (원래 Phase 1.3 목표):
- DDIF (Directional Difference Index) — 방향 차이 지표
- MADDIF (MA of DDIF) — DDIF의 이동평균
- MADDIF1 (15분봉 필터용) — 추세 필터

구현 방식: BinanceTrader의 indicator.py + RCoinFutTrader의 indicators.rs 참조, NumPy 순수 구현
포팅 원본: RCoinFutTrader src/backtester/indicators.rs (799줄), src/strategy/indicators.rs (334줄)
```
**연동**:
- `signal_evaluator.py`에 새 지표 평가 로직 추가 (DDIF 크로스오버 포함)
- `strategy_parser.py` 프롬프트에 37+개 지표 문서화 (DDIF/MADDIF 패턴 포함)

### 2.8 데이터 CSV 캐싱 (2년치)
**파일**: `backend/services/futures/data_loader.py` (확장)
```
변경 (원래 Phase 1.1 목표):
- Binance Futures Klines 2년치 데이터 다운로드 + CSV 로컬 캐싱
- 이후 증분 업데이트 (마지막 타임스탬프 이후만 다운로드)
- 캐시 경로: backend/data/futures_cache/{symbol}_{interval}.csv
- 백테스트 시 API 호출 최소화 → 캐시 우선 사용
포팅 원본: RCoinFutTrader src/backtester/data.rs (550줄)
```

### 2.6 비동기 백테스트 큐 (Celery)
**파일**: `backend/tasks/backtest_task.py` (신규)
```
구현:
- Celery + Redis 백테스트 비동기 실행
- POST /backtest → task_id 반환 (즉시 응답)
- GET /backtest/status/{task_id} → 진행률 (0-100%)
- GET /backtest/result/{task_id} → 완료 시 결과
- WebSocket /ws/backtest/{task_id} → 실시간 진행률 스트리밍
```
**의존성 추가**: `celery>=5.3.0`, `redis>=5.0.0`

### 2.7 Walk-Forward 검증 연동
**파일**: `backend/services/futures/walk_forward.py` (기존, 미연동)
```
변경: 백테스트 라우터에 walk_forward 엔드포인트 추가
POST /backtest/walk-forward → in_sample_days + out_sample_days 기반 검증
```

---

## 6. Phase 3: 실시간 트레이딩 고도화 (5-7일)

### 3.1 WebSocket 가격 피드 + 멀티타임프레임 (REST → WS)
**파일**: `backend/services/demo_price_feed.py` (리팩토링)
```
변경 (원래 Phase 3.1 목표 포함):
- Binance aggTrade WebSocket으로 교체
- CandleManager 구현 (틱 → OHLCV 실시간 집계)
- 300 히스토리컬 바 초기 로드 + 실시간 업데이트
- 멀티타임프레임 지원 (원래 Phase 3.1 핵심 목표):
  - 15분봉 (필터): MADDIF1 > threshold → 매수/매도 준비 상태
  - 3분봉 (트레이드): 준비 상태에서 DDIF 크로스오버 → Long/Short 진입
  - BarAggregator가 1분봉 → 3분봉/15분봉 동시 생성
포팅 원본: RCoinFutTrader src/marketdata/ws.rs, src/marketdata/bars.rs
```

### 3.2 Balance/Position Manager 분리
**파일**:
- `backend/services/trading/balance_manager.py` (신규)
- `backend/services/trading/position_manager.py` (신규)
```
BalanceManager:
  - deduct_margin(amount) → bool (잔고 부족 시 False)
  - release_margin(amount, pnl) → 증거금 반환 + PnL 정산
  - update_unrealized_pnl(total) → 총자산 재계산
  - has_sufficient_balance(required) → bool

PositionManager:
  - open_position(signal, balance_manager) → Position | None
  - close_position(symbol, exit_price, exit_time) → TradeRecord | None
  - update_prices(prices: dict) → 미실현 PnL 갱신
  - FEE_RATE = 0.0004 (0.04%)
```

### 3.3 모의투자 세션 DB 저장
**파일**: `backend/services/supabase_client.py`
```
변경:
- demo_sessions 테이블에 세션 생성/종료 기록
- demo_trades 테이블에 각 거래 기록
- 인메모리 _active_sessions는 Redis 캐시로 교체
- 서버 재시작 시 활성 세션 복구 가능
```

### 3.4 실거래 모드 (Binance API — 시장가 전용)
**파일**:
- `backend/services/trading/live_runner.py` (신규)
- `backend/services/trading/binance_order_api.py` (신규)

> **설계 결정: 시장가(MARKET) 전용**
> 원래 Phase 3.2에 Limit 주문도 계획되어 있었으나, BinanceTrader 설계 문서의 분석 결과
> 시장가 전용이 프로덕션에서 더 안전한 선택이다.
> - 호가 데이터 수신, 미체결 관리, 주문 정정 로직 불필요
> - 즉시 체결 보장 → "주문이 안 잡혔을 때" 로직 불필요
> - 슬리피지 0.01% 고정 시뮬레이션 (실거래는 실제 체결가)
> - **명시적 제외**: 지정가 주문, 분할매수/매도, 변동 레버리지, 호가 데이터

```
LiveRunner:
  - PaperRunner와 동일 파이프라인 (전략 코드 변경 없이 모드만 전환)
  - BinanceOrderAPI.place_market_order(symbol, side, qty) 실주문
  - User stream WebSocket으로 체결 확인
  - SignalDispatcher를 통한 멀티채널 전달
  - DDIF 전략: 15분봉 필터 + 3분봉 진입 (멀티타임프레임 지원)

BinanceOrderAPI:
  - place_market_order(symbol, side, quantity) → OrderResult  # MARKET 전용
  - set_leverage(symbol, leverage)
  - get_account_balance() → float (USDT)
  - get_positions() → list[Position]
  - 타임아웃: 5초
```
**보안**: Binance API Key AES 암호화 저장 (Supabase)

### 3.5 멀티채널 시그널 디스패치
**파일**: `backend/services/dispatch/` (신규 디렉토리)
```
signal_dispatcher.py — 멀티채널 병렬 전송 + 3회 재시도
├── webhook_channel.py — HMAC-SHA256 서명
├── telegram_channel.py — Bot Token + Chat ID
├── discord_channel.py — Discord Webhook URL
└── solana_channel.py — Solana Signal Recording
```

### 3.6 비상 정지 시스템
**파일**: `backend/routers/admin.py` (신규)
```
POST /admin/emergency-stop — 전체 트레이딩 즉시 중지
POST /admin/resume — 트레이딩 재개
GET /admin/status — 플랫폼 상태 조회

구현:
- Redis에 is_paused 플래그 저장
- 모든 트레이딩 엔드포인트에서 플래그 체크
- 활성 세션 일괄 종료
- 관리자 JWT 필수 (role: admin)
```

---

## 7. Phase 4: 블록체인 실제 연동 (7-10일)

### 4.1 실제 Solana TX 전송 구현
**파일**: `backend/services/blockchain/signal_recorder.py` (리팩토링)
```
변경:
- flush_signals_to_chain()에 실제 Solana TX 구성 + 전송
- 서버 키페어로 TX 서명 (SOLANA_PRIVATE_KEY 환경변수)
- TX 확인 후에만 버퍼 삭제 (2PC 패턴)
- 실패 시 재시도 (3회, 지수 백오프)
- 신호 버퍼를 Redis에 저장 (서버 재시작 안전)
```

### 4.2 Signal Sequence 무결성
**파일**: `backend/services/blockchain/signal_recorder.py`
```
변경:
- Supabase에 strategy별 sequence_counter 저장
- 서버 재시작 시 마지막 sequence 복구
- 순번 누락/중복 감지 로직
```

### 4.3 Pyth Oracle 이중 가격 검증
**파일**: `backend/services/blockchain/pyth_client.py` (신규)
```python
class PythClient:
    HERMES_URL = "https://hermes.pyth.network/v2/updates/price/latest"

    SYMBOL_MAP = {
        "BTCUSDT": "0xe62df6c8...",
        "ETHUSDT": "0xff61491a...",
        "SOLUSDT": "0xef0d8b6f...",
    }

    async def get_verified_price(self, symbol: str) -> PythPrice:
        feed_id = self.SYMBOL_MAP.get(symbol)
        resp = await httpx.get(f"{self.HERMES_URL}?ids[]={feed_id}")
        # 5단계 검증:
        # 1. publish_time > now - 30초
        # 2. confidence < price * 2%
        # 3. price > 0
        # 4. status == "Trading"
        # 5. 1e8 스케일 변환
```

### 4.4 NFT 민팅 TX 서명 검증
**파일**: `backend/services/blockchain/strategy_nft.py`
```
변경:
- confirm_mint()에서 실제 TX 검증:
  1. solana RPC getTransaction(tx_signature) 호출
  2. TX 성공 여부 확인 (meta.err == null)
  3. 프로그램 ID 일치 확인
  4. asset_id 존재 확인 (Helius DAS)
```

### 4.5 성능 검증 시스템 (Verified 배지)
**파일**: `backend/services/blockchain/performance_verifier.py` (신규)
```
검증 기준 (StrategyVault 패턴):
- 총 신호 수: >= 100
- 트랙레코드 기간: >= 90일
- 신호 빈도: >= 주 2회 평균
- 독립 검증: >= 3회 → is_verified = true

API:
- POST /blockchain/verify/{strategy_id} — 독립 검증 실행 (누구나)
- GET /blockchain/performance/{strategy_id} — 성과 메트릭 조회
```

### 4.6 Timestamp Integrity
**파일**: `backend/services/blockchain/signal_recorder.py`
```
변경:
- timestamp=0 하드코딩 제거
- 거래 실제 시간 (trade.entry_at, trade.exit_at) 전달
- 온체인 기록 시 Solana Clock::get() 사용 (조작 불가)
- 거래소 시간은 참고용으로만 기록
```

---

## 8. Phase 5: AI 엔진 고도화 (5-7일)

### 5.1 전략 파서 프롬프트 확장
**파일**: `backend/prompts/strategy_parser.py`
```
변경:
- 37개 지표 전체 문서화 (현재 12개)
- 복합 조건 패턴 예시 3개 추가:
  - 추세 확인: "MA 정배열 + RSI > 50 + ADX > 25"
  - 평균회귀: "Bollinger 하단 + RSI < 30 + 거래량 급증"
  - 모멘텀: "MACD 골든크로스 + OBV 상승 + ATR 높음"
- 과적합 경고: "5+ 조건 AND 결합 시 과적합 위험"
- 포지션 사이징 가이드: "총 노출 = positions × leverage ≤ 50%"
```

### 5.2 코칭 프롬프트 강화
**파일**: `backend/prompts/coaching.py`
```
추가 내용:
- IS/OOS 검증 안내 + 과적합 점수 해석 가이드
- 슬리피지/실행 비용 안내 (0.01-0.05%)
- 다중 시간프레임 분석 제안
- 실거래 전환 체크리스트
- 리스크 관리 심화 (Kelly Criterion, 변동성 기반 사이징)
```

### 5.3 AI 모델 듀얼 지원 (Gemini + Claude)
**파일**: `backend/services/ai_client.py` (리팩토링)
```
변경:
- LLMClient 인터페이스 통일
- GeminiClient + ClaudeClient 구현
- 폴백: Gemini 실패 → Claude 자동 전환
- 사용자 설정으로 모델 선택 가능
```

### 5.4 백테스트 결과 분석 프롬프트
**파일**: `backend/prompts/backtest_report.py` (신규)
```
구현:
- 백테스트 결과 + IS/OOS 결과 → AI 분석 리포트
- 강점/약점 자동 식별
- 구체적 개선 제안 (조건 수정, 파라미터 변경)
- 과적합 위험도 경고
```

### 5.5 멀티 심볼 전략 지원
**파일**: `backend/prompts/strategy_parser.py`, 프론트엔드
```
변경:
- target_pair: "SOL/USDC" → target_pairs: ["BTC/USDT", "ETH/USDT"] (최대 5개)
- 백테스트 엔진: 심볼별 독립 실행 + 포트폴리오 합산
- 프론트엔드: 멀티 심볼 선택 UI
```

---

## 9. Phase 6: 마켓플레이스 + 수익화 (7-10일)

### 6.1 전략 마켓플레이스
```
기능:
- 전략 탐색 (필터: verified, 수익률, Sharpe, 가격)
- 전략 상세 (백테스트 차트, 실시간 성과, 신호 히스토리)
- 전략 구매 (SOL 95:5 분배)
- 전략 렌탈 (일일 정산 에스크로)

API:
- GET /marketplace/strategies — 전략 목록 (필터, 정렬, 페이지네이션)
- GET /marketplace/strategies/{id} — 전략 상세 + 성과
- POST /marketplace/purchase — 영구 구매
- POST /marketplace/rent — 기간 대여
- GET /marketplace/my-licenses — 내 라이센스 목록
```

### 6.2 랭킹 시스템
```
점수 공식 (StrategyVault 패턴):
score = (total_return_bps * 40%) + (win_rate_bps * 30%) - (max_drawdown_bps * 30%)
Verified 전략: score *= 2

카테고리:
- Overall (전체)
- Paper Trading (모의투자)
- Live Trading (실거래)
- 심볼별 (BTC, ETH, SOL)

API:
- GET /marketplace/rankings?category=overall&page=1 — Top 100
- GET /marketplace/rankings/featured — 추천 전략
```

### 6.3 에스크로 자동 정산
```
구현 (StrategyVault 패턴):
- 렌탈 SOL → Escrow PDA 예치
- daily_settle (크론 또는 permissionless crank)
  - 경과 일수 계산
  - 일할 정산: 95% → 소유자, 5% → 플랫폼
- expire_rental: 만료 시 잔액 자동 환불

크론: 매일 00:00 UTC 정산 실행
```

### 6.4 수익 대시보드
```
프론트엔드:
- 전략 소유자: 누적 수익, 활성 구독자, 일일 수입
- 구매자: 구매한 전략 목록, 라이센스 상태
- 플랫폼: 총 거래량, 수수료 수입

API:
- GET /marketplace/revenue — 내 전략 수익 요약
- POST /marketplace/claim — 수익 인출
```

---

## 10. Phase 7: 인프라 + 배포 (3-5일)

### 7.1 Docker Compose (로컬 개발)
**파일**: `docker-compose.yml`
```yaml
services:
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: tradecoach
      POSTGRES_USER: tradecoach
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  celery-worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info --concurrency=4
    depends_on: [redis, postgres]

  celery-beat:
    build: ./backend
    command: celery -A tasks beat --loglevel=info
    depends_on: [redis]
```

### 7.2 구조화된 로깅
**파일**: `backend/middleware/logging.py` (신규)
```
변경:
- JSON 구조화 로그 (timestamp, method, path, status, duration_ms, user_id, ip)
- /metrics 엔드포인트: requests_total, errors_total, avg_latency
- Sentry/Datadog 연동 준비
```

### 7.3 헬스체크 + 모니터링
```
GET /health — 서버 상태 + DB 연결 + Redis 연결 + Binance API 상태
GET /health/detailed — RAG 상태, Celery 큐 크기, 활성 세션 수
GET /metrics — Prometheus 포맷 메트릭
```

### 7.4 환경 분리
```
.env.development — 로컬 개발 (devnet, 로컬 DB)
.env.staging — 스테이징 (devnet, Supabase staging)
.env.production — 프로덕션 (mainnet-beta, Supabase prod)
```

### 7.5 프로덕션 배포
```
백엔드: Railway / Fly.io / AWS ECS
- Uvicorn 워커 4개 + Celery 워커 4개
- Redis (Upstash 또는 ElastiCache)
- PostgreSQL (Supabase)

프론트엔드: Vercel
- Next.js 15 SSR
- Edge Functions for API proxy
- Vercel Analytics
```

---

## 11. DB 스키마 확장

```sql
-- Phase 1: 기존 테이블 수정
ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user';  -- user, admin
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN binance_api_key_enc TEXT;
ALTER TABLE users ADD COLUMN binance_secret_key_enc TEXT;

-- Phase 3: 모의투자 영구 저장
CREATE TABLE demo_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  strategy_id UUID REFERENCES strategies(id),
  symbol VARCHAR(20) DEFAULT 'BTCUSDT',
  leverage INTEGER DEFAULT 10,
  status VARCHAR DEFAULT 'active',  -- active, stopped, expired
  initial_balance DECIMAL DEFAULT 1000,
  final_balance DECIMAL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  stopped_at TIMESTAMPTZ
);

CREATE TABLE demo_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES demo_sessions(id),
  side VARCHAR,  -- long, short
  entry_price DECIMAL,
  exit_price DECIMAL,
  quantity DECIMAL,
  leverage INTEGER,
  pnl DECIMAL,
  exit_reason VARCHAR,  -- tp, sl, trailing, liquidation, signal, manual
  entry_at TIMESTAMPTZ,
  exit_at TIMESTAMPTZ
);

-- Phase 4: 블록체인 확장
CREATE TABLE onchain_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  sequence BIGINT NOT NULL,
  signal_hash VARCHAR(64) NOT NULL,
  signal_type VARCHAR NOT NULL,
  symbol VARCHAR(20),
  price DECIMAL,
  pyth_price DECIMAL,
  price_delta_bps INTEGER,
  leverage INTEGER,
  tx_signature VARCHAR(88),  -- Solana TX signature
  confirmed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE signal_sequence (
  strategy_id UUID PRIMARY KEY REFERENCES strategies(id),
  last_sequence BIGINT DEFAULT 0
);

-- Phase 6: 마켓플레이스
CREATE TABLE strategy_listings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id) UNIQUE,
  price_sol DECIMAL NOT NULL,  -- 영구 구매 가격 (SOL)
  rent_sol_per_day DECIMAL,  -- 일일 렌탈 가격 (SOL)
  is_active BOOLEAN DEFAULT TRUE,
  listed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE licenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  licensee_id UUID REFERENCES users(id),
  license_type VARCHAR NOT NULL,  -- permanent, subscription
  price_paid DECIMAL,
  expires_at TIMESTAMPTZ,  -- NULL = 영구
  is_active BOOLEAN DEFAULT TRUE,
  purchased_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE escrow (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  renter_id UUID REFERENCES users(id),
  total_deposited DECIMAL,
  total_settled DECIMAL DEFAULT 0,
  daily_rate DECIMAL,
  last_settled_at TIMESTAMPTZ,
  rental_start TIMESTAMPTZ,
  rental_end TIMESTAMPTZ
);

CREATE TABLE revenue (
  strategy_id UUID PRIMARY KEY REFERENCES strategies(id),
  total_earned DECIMAL DEFAULT 0,
  total_claimed DECIMAL DEFAULT 0,
  platform_fee_earned DECIMAL DEFAULT 0,
  purchase_count INTEGER DEFAULT 0,
  active_rentals INTEGER DEFAULT 0
);

-- Phase 6: 랭킹
CREATE TABLE rankings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category VARCHAR NOT NULL,  -- overall, paper, live, btc, eth, sol
  strategy_id UUID REFERENCES strategies(id),
  score DECIMAL,
  rank INTEGER,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Phase 3: 디스패치 채널
CREATE TABLE dispatch_channels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  channel_type VARCHAR NOT NULL,  -- webhook, telegram, discord, solana
  config JSONB NOT NULL,  -- URL, token, chat_id 등
  enabled BOOLEAN DEFAULT TRUE,
  events JSONB DEFAULT '["signal"]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 12. API 엔드포인트 전체 목록

### 인증 (Auth)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/auth/wallet` | 지갑 nonce 요청 | - |
| POST | `/auth/verify` | 서명 검증 + JWT 발급 | - |
| POST | `/auth/register` | 이메일 가입 | - |
| POST | `/auth/send-verification` | 이메일 인증 코드 발송 | - |
| POST | `/auth/verify-email` | 이메일 인증 확인 | - |
| GET | `/auth/me` | 현재 사용자 정보 | JWT |

### 채팅 (Chat)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/chat/message` | AI 코칭 메시지 | JWT |
| POST | `/chat/message/image` | 차트 이미지 포함 메시지 | JWT |
| WS | `/ws/chat` | AI 채팅 양방향 스트리밍 | JWT |

### 전략 (Strategy)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/strategy` | 전략 생성 (파싱) | JWT |
| GET | `/strategy` | 전략 목록 | JWT |
| GET | `/strategy/{id}` | 전략 상세 | JWT |
| PUT | `/strategy/{id}` | 전략 수정 | JWT |
| DELETE | `/strategy/{id}` | 전략 삭제 | JWT |

### 백테스트 (Backtest)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/backtest` | 백테스트 실행 (비동기, task_id 반환) | JWT |
| GET | `/backtest/status/{task_id}` | 진행률 조회 | JWT |
| GET | `/backtest/result/{task_id}` | 결과 조회 | JWT |
| POST | `/backtest/isoos` | IS/OOS 과적합 검증 | JWT |
| POST | `/backtest/walk-forward` | Walk-Forward 분석 | JWT |
| POST | `/backtest/{id}/report` | AI 분석 리포트 생성 | JWT |
| WS | `/ws/backtest/{task_id}` | 진행률 실시간 스트리밍 | JWT |

### 최적화 (Optimize)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/optimize/grid` | Grid Search 최적화 | JWT |
| GET | `/optimize/result/{task_id}` | 결과 조회 | JWT |

### 트레이딩 (Trading)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/trading/demo/start` | 모의투자 시작 | JWT |
| POST | `/trading/demo/stop` | 모의투자 종료 + 신호 기록 | JWT |
| GET | `/trading/demo/status` | 세션 상태 (포지션, PnL) | JWT |
| GET | `/trading/demo/history` | 거래 내역 | JWT |
| POST | `/trading/live/start` | 실거래 시작 | JWT |
| POST | `/trading/live/stop` | 실거래 종료 | JWT |
| GET | `/trading/live/status` | 실거래 상태 | JWT |
| GET | `/trading/balance` | 잔고 조회 | JWT |
| WS | `/ws/price/{symbol}` | 실시간 가격 스트리밍 | - |
| WS | `/ws/trading` | 주문 체결/잔고 변경 | JWT |

### 블록체인 (Blockchain)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/blockchain/strategy/mint` | cNFT 민팅 준비 | JWT |
| POST | `/blockchain/strategy/confirm` | 민팅 TX 검증 | JWT |
| POST | `/blockchain/strategy/{id}/burn` | cNFT 삭제 | JWT |
| GET | `/blockchain/strategy/{id}/verify` | 무결성 검증 | JWT |
| POST | `/blockchain/signal` | 매매 신호 기록 | JWT |
| GET | `/blockchain/signal/history/{id}` | 신호 히스토리 | - |
| GET | `/blockchain/signal/{id}/proof` | Merkle proof 검증 | - |
| POST | `/blockchain/verify/{id}` | 독립 성능 검증 | JWT |
| GET | `/blockchain/performance/{id}` | 성과 메트릭 | - |
| GET | `/blockchain/signal/buffer/status` | 버퍼 상태 | JWT |
| POST | `/blockchain/signal/flush` | 배치 플러시 | JWT |

### 마켓플레이스 (Marketplace)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| GET | `/marketplace/strategies` | 전략 목록 (필터/정렬) | - |
| GET | `/marketplace/strategies/{id}` | 전략 상세 + 성과 | - |
| POST | `/marketplace/purchase` | 영구 구매 | JWT |
| POST | `/marketplace/rent` | 기간 대여 | JWT |
| GET | `/marketplace/my-licenses` | 내 라이센스 | JWT |
| GET | `/marketplace/rankings` | 랭킹 조회 | - |
| GET | `/marketplace/revenue` | 내 수익 요약 | JWT |
| POST | `/marketplace/claim` | 수익 인출 | JWT |

### 디스패치 (Dispatch)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| GET | `/dispatch/channels` | 채널 목록 | JWT |
| POST | `/dispatch/channels` | 채널 추가 | JWT |
| PUT | `/dispatch/channels/{id}` | 채널 수정 | JWT |
| DELETE | `/dispatch/channels/{id}` | 채널 삭제 | JWT |
| POST | `/dispatch/test/{id}` | 테스트 전송 | JWT |

### 시장 (Market)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| GET | `/market/price/{symbol}` | 실시간 가격 | - |
| GET | `/market/token/info` | 토큰 메타데이터 | - |

### 관리자 (Admin)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| POST | `/admin/emergency-stop` | 비상 정지 | Admin |
| POST | `/admin/resume` | 재개 | Admin |
| GET | `/admin/status` | 플랫폼 상태 | Admin |

### 시스템 (System)
| Method | Path | 설명 | Auth |
|--------|------|------|------|
| GET | `/health` | 서버 상태 | - |
| GET | `/health/detailed` | 상세 상태 | Admin |
| GET | `/metrics` | Prometheus 메트릭 | - |

---

## 13. 테스트 전략

### Unit Tests
```
backend/tests/
├── test_engine.py          — 백테스트 엔진 (PnL, 슬리피지, 청산)
├── test_signal_evaluator.py — 신호 평가 (37개 지표)
├── test_metrics.py          — 메트릭 계산 (Sharpe, CAGR, PF)
├── test_isoos.py            — IS/OOS 과적합 검증
├── test_auth.py             — 인증 (서명 검증, JWT)
├── test_demo_trading.py     — 모의투자 (PnL, 커미션)
├── test_signal_recorder.py  — 신호 기록 (버퍼, 시퀀스)
└── test_dispatch.py         — 디스패치 (멀티채널, 재시도)
```

### Integration Tests
```
backend/tests/integration/
├── test_backtest_flow.py    — 전략 생성 → 백테스트 → 결과
├── test_trading_flow.py     — 세션 시작 → 신호 → 종료 → 기록
├── test_blockchain_flow.py  — 민팅 → 신호 기록 → 검증
└── test_marketplace_flow.py — 리스팅 → 구매 → 라이센스
```

### E2E Tests (Playwright)
```
frontend/tests/
├── auth.spec.ts             — 지갑 연결 → 인증
├── strategy-builder.spec.ts — AI 채팅 → 전략 생성 → 백테스트
├── trading.spec.ts          — 모의투자 플로우
└── marketplace.spec.ts      — 전략 탐색 → 구매
```

### Coverage 목표
- 백엔드: 80%+ (핵심 엔진 95%+)
- 프론트엔드: 60%+ (주요 플로우)
- E2E: 주요 사용자 시나리오 100%

---

## 14. 실행 타임라인

```
Week 1: Phase 0 (긴급 버그) + Phase 1 (보안)
  ├─ Day 1-2: 세션 격리, 메모리 누수, 슬리피지, 커미션
  ├─ Day 3-4: Solana 서명 검증, JWT 수정, 입력 검증
  └─ Day 5: Rate limiting, Helius 보안, 이메일 인증

Week 2: Phase 2 (백테스트 프로덕션화)
  ├─ Day 1-2: 슬리피지 완성, 청산 로직, IS/OOS
  ├─ Day 3-4: 기술 지표 25개 + DDIF/MADDIF 전략 지표 + 프롬프트 업데이트 + CSV 캐싱
  └─ Day 5: Celery 비동기 큐 + Walk-Forward

Week 3: Phase 3 (실시간 트레이딩)
  ├─ Day 1-2: WebSocket 가격 피드 + CandleManager + 멀티타임프레임 (15분+3분)
  ├─ Day 3: Balance/Position Manager 분리
  ├─ Day 4: 세션 DB 저장 + 비상 정지
  └─ Day 5: 멀티채널 디스패치 (Telegram, Discord)

Week 4: Phase 4 (블록체인 실제 연동)
  ├─ Day 1-2: 실제 Solana TX 전송 + Signal Sequence
  ├─ Day 3: Pyth Oracle 이중 가격 검증
  ├─ Day 4: NFT TX 검증 + 성능 검증 시스템
  └─ Day 5: Timestamp Integrity + 테스트

Week 5: Phase 5 (AI 고도화) + Phase 6 시작
  ├─ Day 1-2: 프롬프트 확장 (37개 지표 + 코칭)
  ├─ Day 3: 듀얼 AI 모델 + 결과 분석 프롬프트
  ├─ Day 4-5: 마켓플레이스 기본 (리스팅, 구매)

Week 6: Phase 6 (마켓플레이스) + Phase 7 (인프라)
  ├─ Day 1-2: 렌탈 에스크로 + 랭킹 시스템
  ├─ Day 3: 수익 대시보드
  ├─ Day 4: Docker Compose + 구조화 로깅
  └─ Day 5: 프로덕션 배포 + 모니터링

Week 7: 실거래 모드 + 최종 테스트
  ├─ Day 1-2: Binance 실거래 API + Live Runner
  ├─ Day 3-4: E2E 테스트 + 보안 감사
  └─ Day 5: 스테이징 배포 + 스모크 테스트

Week 8: 프로덕션 런칭
  ├─ Day 1-2: 프로덕션 배포 (mainnet-beta)
  ├─ Day 3: 모니터링 + 알림 설정
  └─ Day 4-5: 안정화 + 핫픽스
```

---

## 의존성 추가 요약

### Python (requirements.txt)
```
# Phase 1: 보안
pynacl>=1.5.0
base58>=2.1.0

# Phase 2: 비동기 큐
celery>=5.3.0
redis>=5.0.0

# Phase 3: 실거래
python-binance>=1.0.19
cryptography>=42.0.0   # API Key AES 암호화

# Phase 4: 블록체인
solana>=0.32.0
solders>=0.21.0

# Phase 5: AI 듀얼
anthropic>=0.40.0      # Claude 폴백

# Phase 7: 모니터링
sentry-sdk[fastapi]>=1.40.0
prometheus-fastapi-instrumentator>=6.1.0
```

### Node.js (frontend/package.json)
```json
{
  "dependencies": {
    "zustand": "^4.5.0",           // 상태 관리
    "@solana/web3.js": "^1.95.0",  // Solana TX
    "lightweight-charts": "^4.1.0", // 차트
    "@tanstack/react-query": "^5.0.0"  // 서버 상태
  }
}
```

---

> **핵심 원칙**: 각 Phase는 독립적으로 배포 가능. Phase 0-1 완료 후 스테이징 배포, Phase 2-3 완료 후 베타 오픈, Phase 4-7 완료 후 프로덕션 런칭.

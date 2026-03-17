# TradeCoach-AI + RCoinFutTrader 통합 구현계획서

> **작성일**: 2026-03-18
> **목표**: RCoinFutTrader(Rust 자동매매)의 핵심 기능을 TradeCoach-AI(웹앱)에 통합

---

## 현재 상태

### TradeCoach-AI (웹앱)
- **프론트엔드**: Next.js 16 + React + Tailwind
- **백엔드**: Python FastAPI + Gemini AI
- **백테스트**: vectorbt 기반 단일 엔진
- **데이터**: Binance Klines REST (최대 41.6일)
- **기능**: 전략 파싱, AI 코칭, 백테스트, i18n(한/영)

### RCoinFutTrader (Rust)
- **코드량**: 18,665줄 Rust
- **핵심**: DDIF 전략, 4개 백테스트 엔진, Walk-Forward v2~v10, Grid/Genetic 최적화
- **데이터**: WebSocket 실시간 + CSV 2년치
- **실거래**: Binance Futures REST API 주문

---

## Phase 1: 백엔드 지표/메트릭 확장 (3일)

### 목표
RCoinFutTrader의 증분형 지표와 성능 메트릭을 Python으로 포팅

### 작업 목록

#### 1.1 지표 확장 (`backend/services/indicators.py` 신규)
- [ ] ADX (Average Directional Index) — 참조: `RCoinFutTrader/src/backtester/indicators.rs`
- [ ] DI+/DI- (Directional Indicator)
- [ ] Stochastic RSI (K/D 라인)
- [ ] ATR (Average True Range)
- [ ] VWAP (Volume Weighted Average Price)
- [ ] EMA cross (short/long)
- **포팅 원본**: `src/backtester/indicators.rs` (799줄), `src/strategy/indicators.rs` (334줄)

#### 1.2 메트릭 확장 (`backend/services/metrics.py` 신규)
- [ ] CAGR (연평균 복합 수익률)
- [ ] Profit Factor (총이익/총손실)
- [ ] Calmar Ratio (CAGR/MDD)
- [ ] Average Win/Loss 비율
- [ ] Maximum Consecutive Losses
- **포팅 원본**: `src/backtester/metrics.rs` (487줄)

#### 1.3 현실적 시뮬레이션 개선 (`backend/services/backtest_engine.py` 수정)
- [ ] 슬리피지 모델 추가 (1~2틱 기본)
- [ ] 수수료 정밀화 (maker/taker 구분, 기본 0.04%)
- [ ] 분할 익절 (Partial Exit) 로직
- [ ] 추적 손절 (Trailing Stop) 로직
- **포팅 원본**: `src/app/mod.rs` (343줄) DemoEngine의 리스크 관리 로직

### API 변경
- `POST /backtest/run` 응답에 확장 메트릭 추가 (기존 호환 유지)
- 프론트엔드 `BacktestResult` 타입에 새 메트릭 필드 추가 (optional)

---

## Phase 2: 파라미터 최적화 엔진 (5일)

### 목표
사용자 전략의 최적 파라미터를 자동 탐색하는 기능 추가

### 작업 목록

#### 2.1 Grid Search 최적화 (`backend/services/optimizer.py` 신규)
- [ ] 파라미터 범위 정의 (JSON 스키마)
- [ ] Grid 조합 생성 + 병렬 백테스트 실행
- [ ] 목적 함수: Sharpe Ratio, Total Return, MDD 기반 복합 점수
- [ ] 상위 N개 결과 반환
- **포팅 원본**: `src/backtester/optimizer.rs` (601줄)

#### 2.2 Walk-Forward 분석 (`backend/services/walk_forward.py` 신규)
- [ ] 데이터 기간 분할: In-Sample (훈련) / Out-of-Sample (검증)
- [ ] Rolling Window 방식 (Anchored + Sliding)
- [ ] OOS 성과 집계 → 과적합 판정
- [ ] 최적 파라미터 → 최종 추천
- **포팅 원본**: `src/backtester/ddif_optimizer.rs` (1,161줄) Walk-Forward 로직

#### 2.3 API 엔드포인트
- [ ] `POST /backtest/optimize` — Grid Search 실행
  ```json
  {
    "strategy_id": "...",
    "param_ranges": {
      "rsi_period": [10, 14, 20],
      "take_profit": [5, 8, 10, 15],
      "stop_loss": [-3, -5, -8]
    },
    "objective": "sharpe",
    "max_combinations": 100
  }
  ```
- [ ] `POST /backtest/walk-forward` — Walk-Forward 분석 실행
  ```json
  {
    "strategy_id": "...",
    "in_sample_days": 270,
    "out_sample_days": 90,
    "windows": 4
  }
  ```

#### 2.4 프론트엔드 UI
- [ ] 전략 상세 페이지에 "최적화" 버튼 추가
- [ ] 최적화 결과 테이블 (상위 10개 파라미터 조합)
- [ ] Walk-Forward 결과 차트 (In/Out 수익률 비교)

---

## Phase 3: 실시간 데이터 & 모의투자 (7일)

### 목표
실시간 가격 스트리밍 + 전략 기반 모의투자 모드

### 작업 목록

#### 3.1 WebSocket 가격 스트리밍 (`backend/services/binance_ws.py` 신규)
- [ ] Binance aggTrade WebSocket 연결
- [ ] N분봉 BarAggregator (틱 → OHLCV 변환)
- [ ] FastAPI WebSocket 엔드포인트 (`/ws/price/{symbol}`)
- [ ] 프론트엔드 실시간 차트 컴포넌트
- **포팅 원본**: `src/marketdata/ws.rs` (실시간 스트림), `src/marketdata/bars.rs` (바 집계)

#### 3.2 모의투자 엔진 (`backend/services/demo_trading.py` 신규)
- [ ] 가상 포지션 관리 (Long/Short/반전)
- [ ] 가상 잔고 추적
- [ ] 주문 타입: Market, Limit
- [ ] SL/TP/Trailing Stop 자동 관리
- [ ] 거래 내역 Supabase 저장
- **포팅 원본**: `src/app/mod.rs` (DemoEngine), `src/app/runner.rs` (DemoRunner)

#### 3.3 API 엔드포인트
- [ ] `POST /trading/demo/start` — 모의투자 세션 시작
- [ ] `POST /trading/demo/stop` — 모의투자 세션 종료
- [ ] `GET /trading/demo/status` — 현재 포지션/잔고 조회
- [ ] `GET /trading/demo/history` — 거래 내역 조회

#### 3.4 프론트엔드 UI
- [ ] 모의투자 대시보드 페이지 (`/trading`)
- [ ] 실시간 포지션 카드 (수익률, PnL)
- [ ] 실시간 가격 차트 (lightweight-charts WebSocket 연동)
- [ ] 거래 히스토리 테이블

---

## Phase 4: Rust 고속 백테스트 브릿지 (선택, 5일)

### 목표
대량 최적화 시 Rust 바이너리 직접 활용으로 10~100배 속도 향상

### 작업 목록

#### 4.1 Rust HTTP 브릿지 (`RCoinFutTrader/src/bin/api_server.rs` 신규)
- [ ] Axum/Actix 경량 HTTP 서버
- [ ] `POST /backtest` — JSON 전략 입력 → 백테스트 결과 JSON 출력
- [ ] `POST /optimize` — 파라미터 범위 → 최적화 결과
- [ ] Docker 컨테이너화

#### 4.2 Python 클라이언트 (`backend/services/rust_bridge.py` 신규)
- [ ] HTTP 클라이언트 (httpx async)
- [ ] 폴백: Rust 서버 불가 시 Python 엔진 사용
- [ ] 결과 포맷 변환 (Rust JSON → Python dict)

---

## 데이터 확장 계획

| 현재 | 목표 | 방법 |
|------|------|------|
| Binance REST 41.6일 | 최대 2년 | `scripts/download_data.sh` 포팅, CSV 캐싱 |
| SOL/USDC only | 멀티 심볼 | 프론트엔드 심볼 선택 UI |
| 1h/4h/1d | 1m/3m/5m/15m/1h/4h/1d | 다중 타임프레임 지원 |

---

## DB 스키마 확장

```sql
-- 최적화 결과 테이블
CREATE TABLE optimization_results (
  id UUID PRIMARY KEY,
  strategy_id UUID REFERENCES strategies(id),
  method TEXT, -- 'grid' | 'genetic' | 'walk_forward'
  params JSONB,
  metrics JSONB,
  rank INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 모의투자 세션 테이블
CREATE TABLE demo_sessions (
  id UUID PRIMARY KEY,
  user_id UUID,
  strategy_id UUID,
  status TEXT, -- 'active' | 'stopped'
  initial_balance DECIMAL,
  current_balance DECIMAL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  stopped_at TIMESTAMPTZ
);

-- 모의투자 거래 내역
CREATE TABLE demo_trades (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES demo_sessions(id),
  side TEXT, -- 'long' | 'short'
  entry_price DECIMAL,
  exit_price DECIMAL,
  quantity DECIMAL,
  pnl DECIMAL,
  entry_at TIMESTAMPTZ,
  exit_at TIMESTAMPTZ
);
```

---

## 일정 요약

| Phase | 내용 | 기간 | 의존성 |
|-------|------|------|--------|
| **Phase 1** | 지표/메트릭/시뮬레이션 확장 | 3일 | 없음 (독립) |
| **Phase 2** | 파라미터 최적화 + Walk-Forward | 5일 | Phase 1 |
| **Phase 3** | 실시간 데이터 + 모의투자 | 7일 | Phase 1 |
| **Phase 4** | Rust 고속 브릿지 (선택) | 5일 | Phase 2 |
| **총 예상** | Phase 1~3 필수 | **~15일** | |

---

## 기술 결정 사항

| 결정 | 선택 | 이유 |
|------|------|------|
| 지표 구현 | Python (ta-lib/pandas) | 유지보수 용이, Rust FFI 복잡도 회피 |
| 최적화 | Python (multiprocessing) | 기존 백엔드와 통합 용이 |
| 실시간 WS | Python (websockets) | FastAPI WebSocket 네이티브 지원 |
| 모의투자 | Python + Supabase | 기존 인프라 활용 |
| Rust 브릿지 | HTTP API (선택) | 속도 필요 시에만 도입, 독립 배포 |

---

## 참조 파일 매핑 (RCoinFutTrader → TradeCoach-AI)

| RCoinFutTrader 원본 | 포팅 대상 | 줄 수 |
|---------------------|----------|-------|
| `src/backtester/indicators.rs` | `backend/services/indicators.py` | 799 |
| `src/backtester/metrics.rs` | `backend/services/metrics.py` | 487 |
| `src/backtester/optimizer.rs` | `backend/services/optimizer.py` | 601 |
| `src/backtester/ddif_optimizer.rs` | `backend/services/walk_forward.py` | 1,161 |
| `src/backtester/realistic_engine.rs` | `backend/services/backtest_engine.py` 확장 | 1,002 |
| `src/app/mod.rs` + `runner.rs` | `backend/services/demo_trading.py` | 1,235 |
| `src/marketdata/ws.rs` + `bars.rs` | `backend/services/binance_ws.py` | ~700 |
| `src/strategy/logic.rs` | AI 프롬프트에 전략 로직 반영 | 492 |

# TradeCoach-AI + RCoinFutTrader 통합 구현계획서 v2

> **작성일**: 2026-03-18
> **핵심 변경**: RCoinFutTrader(선물 자동매매)를 기반 엔진으로 채택. 현물 → 선물 전환.

---

## 설계 원칙

**RCoinFutTrader가 엔진, TradeCoach-AI가 UI**

```
TradeCoach-AI (웹 UI)          RCoinFutTrader (엔진)
┌─────────────────┐           ┌──────────────────────┐
│ Next.js 프론트엔드 │ ← API → │ Python 백엔드          │
│ AI 채팅/코칭     │           │   ↕ Rust 백테스트 브릿지 │
│ 전략 빌더        │           │   ↕ Binance Futures API│
│ 결과 시각화      │           │   ↕ WebSocket 실시간    │
└─────────────────┘           └──────────────────────┘
```

---

## 현재 vs 통합 후

| 항목 | 현재 (Spot) | 통합 후 (Futures) |
|------|------------|------------------|
| **시장** | 현물 | **USDT-M 선물** |
| **포지션** | 매수만 | **Long + Short** |
| **레버리지** | 1x 고정 | **1x~125x 설정 가능** |
| **수수료** | 0.3% | **0.04% (Futures)** |
| **데이터** | Binance Spot Klines 41일 | **Futures Klines + CSV 2년치** |
| **리스크** | TP/SL만 | **TP/SL + 분할익절 + 추적손절 + 강제청산** |
| **백테스트 엔진** | Python vectorbt 1개 | **Python 정밀엔진 + Rust 고속엔진** |
| **최적화** | 없음 | **Grid/Genetic + Walk-Forward** |
| **모의투자** | 없음 | **호가 기반 시뮬레이션** |
| **전략** | 범용 지표 | **DDIF + 범용 지표 + 멀티타임프레임** |

---

## Phase 1: 선물 백테스트 엔진 전환 (5일)

### 목표
기존 현물 백테스트를 선물(Futures) 기반으로 완전 교체

### 1.1 데이터 소스 전환
- [ ] Binance Futures Klines API 엔드포인트 변경 (`/fapi/v1/klines`)
- [ ] 과거 데이터 다운로드 스크립트 포팅 (`scripts/download_data.sh` → Python)
- [ ] CSV 캐싱 (2년치 데이터 로컬 저장, 이후 증분 업데이트)
- **포팅 원본**: `src/backtester/data.rs` (550줄)

### 1.2 선물 백테스트 엔진 (`backend/services/futures_engine.py` 신규)
- [ ] Long/Short 양방향 포지션 지원
- [ ] 레버리지 설정 (1x~125x)
- [ ] 수수료 0.04% (maker/taker 구분)
- [ ] 분할 익절 (Partial Exit): 1차 목표에서 50% 청산
- [ ] 추적 손절 (Trailing Stop): 최고점 대비 콜백 비율
- [ ] 강제 청산 (Liquidation) 가격 계산
- [ ] 슬리피지 모델 (1~2틱)
- **포팅 원본**: `src/backtester/realistic_engine.rs` (1,002줄), `src/app/mod.rs` (343줄)

### 1.3 지표 확장 (`backend/services/indicators.py` 신규)
- [ ] ADX (Average Directional Index) — 추세 강도
- [ ] DI+/DI- (Directional Indicator) — 추세 방향
- [ ] DDIF/MADDIF — RCoinFutTrader 핵심 전략 지표
- [ ] Stochastic RSI (K/D 라인)
- [ ] ATR (Average True Range)
- [ ] EMA cross (short/long period)
- [ ] 증분형 계산 (전체 재계산 없이 새 봉만 업데이트)
- **포팅 원본**: `src/backtester/indicators.rs` (799줄), `src/strategy/indicators.rs` (334줄)

### 1.4 성능 메트릭 확장 (`backend/services/metrics.py` 신규)
- [ ] CAGR (연평균 복합 수익률)
- [ ] Profit Factor (총이익/총손실)
- [ ] Calmar Ratio (CAGR/MDD)
- [ ] Average Win/Loss 비율
- [ ] Maximum Consecutive Losses
- [ ] Long/Short 별도 통계
- **포팅 원본**: `src/backtester/metrics.rs` (487줄)

### 1.5 전략 JSON 스키마 확장
기존 전략 JSON에 선물 전용 필드 추가:
```json
{
  "market_type": "futures",
  "leverage": 10,
  "direction": "both",
  "risk": {
    "stop_loss": -0.4,
    "take_profit": 1.5,
    "partial_exit": { "enabled": true, "at_pct": 1.2, "ratio": 0.5 },
    "trailing_stop": { "enabled": true, "trigger_pct": 0.9, "callback_pct": 0.2 }
  },
  "filter_interval": 15,
  "trade_interval": 3
}
```

### 1.6 API 변경
- `POST /backtest/run` — `market_type: "futures"` 기본값 변경
- 응답에 확장 메트릭 + Long/Short 별도 통계 추가
- 프론트엔드 BacktestResult 컴포넌트에 레버리지/방향 표시

### 1.7 AI 프롬프트 업데이트
- 코칭 프롬프트에 선물 리스크 관리 프레임워크 추가 (레버리지 위험, 강제청산 교육)
- 전략 파서에 선물 전용 필드 인식 추가

---

## Phase 2: 파라미터 최적화 + Walk-Forward (5일)

### 2.1 Grid Search 최적화 (`backend/services/optimizer.py` 신규)
- [ ] 파라미터 범위 정의 (레버리지, TP/SL, 지표 파라미터)
- [ ] 선물 백테스트 엔진으로 병렬 실행 (multiprocessing)
- [ ] 목적 함수: Sharpe, Calmar, Profit Factor 기반 복합 점수
- [ ] 상위 N개 결과 반환
- **포팅 원본**: `src/backtester/optimizer.rs` (601줄)

### 2.2 Walk-Forward 전진분석 (`backend/services/walk_forward.py` 신규)
- [ ] 데이터 기간 분할: In-Sample (훈련) / Out-of-Sample (검증)
- [ ] Rolling Window 방식 (Anchored + Sliding)
- [ ] OOS 성과 집계 → 과적합 판정 (IS 대비 50% 이상이면 유효)
- [ ] 최적 파라미터 → 최종 추천
- **포팅 원본**: `src/backtester/ddif_optimizer.rs` (1,161줄)

### 2.3 API 엔드포인트
- [ ] `POST /backtest/optimize`
  ```json
  {
    "strategy_id": "...",
    "param_ranges": {
      "leverage": [5, 10, 20],
      "take_profit": [1.0, 1.5, 2.0],
      "stop_loss": [-0.3, -0.4, -0.5],
      "rsi_period": [10, 14, 20]
    },
    "objective": "sharpe",
    "max_combinations": 100
  }
  ```
- [ ] `POST /backtest/walk-forward`
  ```json
  {
    "strategy_id": "...",
    "in_sample_days": 270,
    "out_sample_days": 90,
    "windows": 4
  }
  ```

### 2.4 프론트엔드 UI
- [ ] 전략 상세 페이지에 "Optimize" 버튼
- [ ] 최적화 결과 테이블 (상위 10개 파라미터 조합 + 메트릭)
- [ ] "Walk-Forward" 버튼 → IS/OOS 비교 차트
- [ ] 과적합 판정 배지 (Pass/Fail)

---

## Phase 3: 실시간 데이터 + 모의투자 (7일)

### 3.1 WebSocket 가격 스트리밍 (`backend/services/binance_ws.py` 신규)
- [ ] Binance Futures aggTrade WebSocket 연결
- [ ] N분봉 BarAggregator (틱 → OHLCV 변환)
- [ ] 15분봉 (필터) + 3분봉 (트레이드) 멀티타임프레임
- [ ] FastAPI WebSocket 엔드포인트 (`/ws/price/{symbol}`)
- **포팅 원본**: `src/marketdata/ws.rs`, `src/marketdata/bars.rs`

### 3.2 모의투자 엔진 (`backend/services/demo_trading.py` 신규)
- [ ] 가상 포지션 관리 (Long/Short/반전)
- [ ] 레버리지 반영 잔고 계산
- [ ] 주문 타입: Market, Limit
- [ ] SL/TP/분할익절/추적손절 자동 관리
- [ ] 강제 청산 시뮬레이션
- [ ] 거래 내역 Supabase 저장
- **포팅 원본**: `src/app/mod.rs` (DemoEngine), `src/app/runner.rs` (DemoRunner)

### 3.3 DDIF 전략 엔진 (`backend/services/ddif_strategy.py` 신규)
- [ ] 15분봉 필터: MADDIF1 > threshold → 매수/매도 준비 상태
- [ ] 3분봉 진입: 준비 상태에서 MADDIF 크로스오버 → Long/Short 진입
- [ ] 15분봉 반전 신호 → 포지션 청산
- **포팅 원본**: `src/strategy/logic.rs` (492줄)

### 3.4 API 엔드포인트
- [ ] `POST /trading/demo/start` — 모의투자 세션 시작 (전략+심볼+레버리지)
- [ ] `POST /trading/demo/stop` — 모의투자 세션 종료
- [ ] `GET /trading/demo/status` — 현재 포지션/잔고/PnL
- [ ] `GET /trading/demo/history` — 거래 내역

### 3.5 프론트엔드 (`/trading` 신규 페이지)
- [ ] 실시간 가격 차트 (lightweight-charts WebSocket 연동)
- [ ] 포지션 카드 (Long/Short, 레버리지, 미실현 PnL)
- [ ] 잔고/마진 표시
- [ ] 거래 히스토리 테이블
- [ ] 시작/중지 버튼

---

## Phase 4: Rust 고속 백테스트 브릿지 (선택, 5일)

### 4.1 Rust HTTP API (`RCoinFutTrader/src/bin/api_server.rs` 신규)
- [ ] Axum 경량 HTTP 서버
- [ ] `POST /backtest` — JSON 전략 → 백테스트 결과
- [ ] `POST /optimize` — 파라미터 범위 → Grid/Genetic 최적화
- [ ] `POST /walk-forward` — Walk-Forward 전진분석
- [ ] Docker 컨테이너화

### 4.2 Python 클라이언트 (`backend/services/rust_bridge.py` 신규)
- [ ] httpx async 클라이언트
- [ ] 폴백: Rust 서버 불가 시 Python 엔진 사용
- [ ] 결과 포맷 변환

---

## DB 스키마 확장

```sql
-- 최적화 결과
CREATE TABLE optimization_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  method TEXT, -- 'grid' | 'genetic' | 'walk_forward'
  params JSONB,
  metrics JSONB,
  rank INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 모의투자 세션
CREATE TABLE demo_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  strategy_id UUID,
  symbol VARCHAR(20) DEFAULT 'BTCUSDT',
  leverage INTEGER DEFAULT 10,
  status TEXT DEFAULT 'active',
  initial_balance DECIMAL DEFAULT 1000,
  current_balance DECIMAL DEFAULT 1000,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  stopped_at TIMESTAMPTZ
);

-- 모의투자 거래 내역
CREATE TABLE demo_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES demo_sessions(id),
  side TEXT, -- 'long' | 'short'
  entry_price DECIMAL,
  exit_price DECIMAL,
  quantity DECIMAL,
  leverage INTEGER,
  pnl DECIMAL,
  exit_reason TEXT, -- 'tp' | 'sl' | 'trailing' | 'liquidation' | 'signal'
  entry_at TIMESTAMPTZ,
  exit_at TIMESTAMPTZ
);
```

---

## Phase 5: 블록체인 통합 (7일)

### 목표
전략과 거래 신호를 블록체인에 기록하여 무결성 보장. 전략은 등록/삭제만 가능 (수정 불가).

### 5.1 전략 온체인 등록 (`backend/services/blockchain.py` 신규)
- [ ] Solana Program (스마트 컨트랙트) 설계
  - 전략 등록: JSON 해시 + 메타데이터 → 온체인 저장
  - 전략 삭제: 소유자만 삭제 가능 (등록자 검증)
  - **수정 불가**: 등록 후 변경 차단 (immutable)
- [ ] 전략 등록 시 JSON 전체를 IPFS/Arweave에 저장, 해시만 온체인
- [ ] 등록된 전략 조회 API
- [ ] 프론트엔드 "Register on Chain" 버튼

### 5.2 거래 신호 트랜잭션 기록
- [ ] 매매 신호 발생 시 자동으로 Solana 트랜잭션 생성
  - 신호 타입 (Long/Short/Close)
  - 타임스탬프
  - 전략 ID (온체인 참조)
  - 진입/청산 가격
- [ ] 신호 히스토리 온체인 조회
- [ ] 트랜잭션 비용 최소화 (배치 처리 또는 압축)

### 5.3 무결성 검증
- [ ] 전략 변경 감지: DB 전략 vs 온체인 해시 비교
- [ ] 거래 내역 감사 추적: 온체인 기록 vs 로컬 DB 일치 확인
- [ ] 프론트엔드 "Verified" 배지 (온체인 등록 전략)

### 5.4 API 엔드포인트
- [ ] `POST /blockchain/strategy/register` — 전략 온체인 등록
- [ ] `DELETE /blockchain/strategy/{id}` — 전략 온체인 삭제
- [ ] `GET /blockchain/strategy/{id}/verify` — 무결성 검증
- [ ] `POST /blockchain/signal` — 거래 신호 트랜잭션 기록
- [ ] `GET /blockchain/signal/history/{strategy_id}` — 신호 히스토리 조회

### 5.5 기술 선택지

| 방식 | 장점 | 단점 |
|------|------|------|
| **Solana Program** | 기존 Phantom 연동 활용 | 개발 복잡도 높음 |
| **Anchor Framework** | Solana 개발 간소화 | Rust 필요 |
| **IPFS + Solana 해시** | 저비용, 대용량 데이터 | 2단계 조회 |
| **Arweave** | 영구 저장 | 별도 비용 |

### 5.6 DB 스키마 추가

```sql
-- 온체인 전략 등록 기록
CREATE TABLE onchain_strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  tx_signature VARCHAR(88) NOT NULL,
  onchain_hash VARCHAR(64) NOT NULL,
  ipfs_cid TEXT,
  registered_at TIMESTAMPTZ DEFAULT NOW()
);

-- 온체인 거래 신호
CREATE TABLE onchain_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  signal_type TEXT NOT NULL, -- 'long_entry' | 'short_entry' | 'close'
  price DECIMAL,
  tx_signature VARCHAR(88) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 일정 요약

| Phase | 내용 | 기간 | 의존성 |
|-------|------|------|--------|
| **Phase 1** | 선물 백테스트 엔진 전환 | 5일 | 없음 |
| **Phase 2** | 최적화 + Walk-Forward | 5일 | Phase 1 |
| **Phase 3** | 실시간 + 모의투자 | 7일 | Phase 1 |
| **Phase 4** | Rust 고속 브릿지 (선택) | 5일 | Phase 2 |
| **Phase 5** | 블록체인 통합 | 7일 | Phase 3 |
| **총 예상** | Phase 1~3 + 5 필수 | **~24일** | |

---

## 참조 파일 매핑 (RCoinFutTrader → TradeCoach-AI)

| RCoinFutTrader 원본 | → TradeCoach-AI | 줄 수 | Phase |
|---------------------|-----------------|-------|-------|
| `backtester/realistic_engine.rs` | `services/futures_engine.py` | 1,002 | 1 |
| `backtester/indicators.rs` | `services/indicators.py` | 799 | 1 |
| `strategy/indicators.rs` | `services/indicators.py` | 334 | 1 |
| `backtester/metrics.rs` | `services/metrics.py` | 487 | 1 |
| `backtester/data.rs` | `services/data_loader.py` | 550 | 1 |
| `backtester/optimizer.rs` | `services/optimizer.py` | 601 | 2 |
| `backtester/ddif_optimizer.rs` | `services/walk_forward.py` | 1,161 | 2 |
| `marketdata/ws.rs` + `bars.rs` | `services/binance_ws.py` | ~700 | 3 |
| `app/mod.rs` + `runner.rs` | `services/demo_trading.py` | 1,235 | 3 |
| `strategy/logic.rs` | `services/ddif_strategy.py` | 492 | 3 |

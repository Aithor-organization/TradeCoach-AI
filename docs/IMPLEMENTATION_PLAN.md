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
- [x] Binance Futures Klines API 엔드포인트 변경 (`/fapi/v1/klines`)
- [x] 과거 데이터 다운로드 스크립트 포팅 (`scripts/download_data.sh` → Python)
- [x] CSV 캐싱 (2년치 데이터 로컬 저장, 이후 증분 업데이트)
- **포팅 원본**: `src/backtester/data.rs` (550줄)

### 1.2 선물 백테스트 엔진 (`backend/services/futures_engine.py` 신규)
- [x] Long/Short 양방향 포지션 지원
- [x] 레버리지 설정 (1x~125x)
- [x] 수수료 0.04% (maker/taker 구분)
- [x] 분할 익절 (Partial Exit): 1차 목표에서 50% 청산
- [x] 추적 손절 (Trailing Stop): 최고점 대비 콜백 비율
- [x] 강제 청산 (Liquidation) 가격 계산
- [x] 슬리피지 모델 (1~2틱)
- **포팅 원본**: `src/backtester/realistic_engine.rs` (1,002줄), `src/app/mod.rs` (343줄)

### 1.3 지표 확장 (`backend/services/indicators.py` 신규)
- [x] ADX (Average Directional Index) — 추세 강도
- [x] DI+/DI- (Directional Indicator) — 추세 방향
- [x] DDIF/MADDIF — RCoinFutTrader 핵심 전략 지표
- [x] Stochastic RSI (K/D 라인)
- [x] ATR (Average True Range)
- [x] EMA cross (short/long period)
- [x] 증분형 계산 (전체 재계산 없이 새 봉만 업데이트)
- **포팅 원본**: `src/backtester/indicators.rs` (799줄), `src/strategy/indicators.rs` (334줄)

### 1.4 성능 메트릭 확장 (`backend/services/metrics.py` 신규)
- [x] CAGR (연평균 복합 수익률)
- [x] Profit Factor (총이익/총손실)
- [x] Calmar Ratio (CAGR/MDD)
- [x] Average Win/Loss 비율
- [x] Maximum Consecutive Losses
- [x] Long/Short 별도 통계
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
- [x] 파라미터 범위 정의 (레버리지, TP/SL, 지표 파라미터)
- [x] 선물 백테스트 엔진으로 병렬 실행 (multiprocessing)
- [x] 목적 함수: Sharpe, Calmar, Profit Factor 기반 복합 점수
- [x] 상위 N개 결과 반환
- **포팅 원본**: `src/backtester/optimizer.rs` (601줄)

### 2.2 Walk-Forward 전진분석 (`backend/services/walk_forward.py` 신규)
- [x] 데이터 기간 분할: In-Sample (훈련) / Out-of-Sample (검증)
- [x] Rolling Window 방식 (Anchored + Sliding)
- [x] OOS 성과 집계 → 과적합 판정 (IS 대비 50% 이상이면 유효)
- [x] 최적 파라미터 → 최종 추천
- **포팅 원본**: `src/backtester/ddif_optimizer.rs` (1,161줄)

### 2.3 API 엔드포인트
- [x] `POST /backtest/optimize`
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
- [x] `POST /backtest/walk-forward`
  ```json
  {
    "strategy_id": "...",
    "in_sample_days": 270,
    "out_sample_days": 90,
    "windows": 4
  }
  ```

### 2.4 프론트엔드 UI
- [x] 전략 상세 페이지에 "Optimize" 버튼
- [x] 최적화 결과 테이블 (상위 10개 파라미터 조합 + 메트릭)
- [x] "Walk-Forward" 버튼 → IS/OOS 비교 차트
- [x] 과적합 판정 배지 (Pass/Fail)

---

## Phase 3: 실시간 데이터 + 모의투자 (7일)

### 3.1 WebSocket 가격 스트리밍 (`backend/services/binance_ws.py` 신규)
- [x] Binance Futures aggTrade WebSocket 연결
- [x] N분봉 BarAggregator (틱 → OHLCV 변환)
- [x] 15분봉 (필터) + 3분봉 (트레이드) 멀티타임프레임
- [x] FastAPI WebSocket 엔드포인트 (`/ws/price/{symbol}`)
- **포팅 원본**: `src/marketdata/ws.rs`, `src/marketdata/bars.rs`

### 3.2 모의투자 엔진 (`backend/services/demo_trading.py` 신규)
- [x] 가상 포지션 관리 (Long/Short/반전)
- [x] 레버리지 반영 잔고 계산
- [x] 주문 타입: Market, Limit
- [x] SL/TP/분할익절/추적손절 자동 관리
- [x] 강제 청산 시뮬레이션
- [x] 거래 내역 Supabase 저장
- **포팅 원본**: `src/app/mod.rs` (DemoEngine), `src/app/runner.rs` (DemoRunner)

### 3.3 DDIF 전략 엔진 (`backend/services/ddif_strategy.py` 신규)
- [x] 15분봉 필터: MADDIF1 > threshold → 매수/매도 준비 상태
- [x] 3분봉 진입: 준비 상태에서 MADDIF 크로스오버 → Long/Short 진입
- [x] 15분봉 반전 신호 → 포지션 청산
- **포팅 원본**: `src/strategy/logic.rs` (492줄)

### 3.4 API 엔드포인트
- [x] `POST /trading/demo/start` — 모의투자 세션 시작 (전략+심볼+레버리지)
- [x] `POST /trading/demo/stop` — 모의투자 세션 종료
- [x] `GET /trading/demo/status` — 현재 포지션/잔고/PnL
- [x] `GET /trading/demo/history` — 거래 내역

### 3.5 프론트엔드 (`/trading` 신규 페이지)
- [x] 실시간 가격 차트 (lightweight-charts WebSocket 연동)
- [x] 포지션 카드 (Long/Short, 레버리지, 미실현 PnL)
- [x] 잔고/마진 표시
- [x] 거래 히스토리 테이블
- [x] 시작/중지 버튼

---

## Phase 4: Rust 고속 백테스트 브릿지 (선택, 5일) — **보류**

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

## Phase 5: 블록체인 통합 — 상태 압축 + cNFT (7일)

### 목표
**Solana State Compression**을 활용하여 전략을 cNFT로 등록하고, 매매 신호를 Merkle Tree에 압축 기록.
전략은 등록/삭제만 가능 (수정 불가). 비용: 100만 건 신호 기록에 ~$1.

### 아키텍처

```
전략 생성 → cNFT 민팅 (Bubblegum, isMutable: false)
               ├── 메타데이터: 전략명, 전략 JSON 해시(SHA256)
               ├── 원본 JSON → Arweave/IPFS 영구 저장
               └── 소유자만 burn(삭제) 가능

모의투자 실행 → 매매 신호 발생
               ├── 신호 데이터 SHA256 해시 생성
               ├── Merkle Tree에 압축 리프로 append
               └── 원본 데이터 → Helius DAS API 인덱서에 자동 저장

검증/조회 → Helius DAS API
               ├── getAssetsByGroup → 전략 cNFT + 신호 리프 목록
               ├── getAssetProof → Merkle proof로 무결성 검증
               └── DB 해시 vs 온체인 해시 비교 → "Verified" 배지
```

### 5.1 Merkle Tree 설정

- [x] 앱 초기화 시 Concurrent Merkle Tree 생성 (한 번)
  - `maxDepth: 20` → 최대 1,048,576개 리프
  - `maxBufferSize: 64` → 동시 쓰기 지원
  - 비용: ~$0.05 (tree 생성 rent)
- [x] Tree authority = 백엔드 서버 키페어 (자동 신호 기록용)

### 5.2 전략 cNFT 민팅 (`backend/services/blockchain.py` 신규)

- [x] 전략 JSON → SHA256 해시 생성
- [x] Bubblegum `mintToCollectionV1`로 cNFT 민팅
  ```
  metadata:
    name: "Strategy: DDIF BTC 15m"
    uri: "arweave://..." (전략 JSON 전체)
    attributes:
      strategy_hash: "a3f2c8..."
      created_by: "user_wallet_or_email"
      immutable: true
  ```
- [x] `isMutable: false` 설정 → 민팅 후 수정 불가
- [x] burn (삭제): 소유자 서명 필요
- **비용: ~$0.00005/전략**

### 5.3 매매 신호 압축 기록

- [x] 모의투자 엔진에서 신호 발생 시 자동 호출
- [x] 신호 데이터 구조:
  ```json
  {
    "strategy_nft_id": "...",
    "signal_type": "long_entry",
    "symbol": "BTCUSDT",
    "price": 65000.50,
    "leverage": 10,
    "timestamp": 1710720000
  }
  ```
- [x] SHA256(signal_data) → Merkle Tree 리프로 append
- [x] 원본 데이터는 Helius 인덱서가 자동 저장 (DAS API로 조회)
- **비용: ~$0.00001/신호** (100만 건 = ~$1)

### 5.4 조회 + 검증

- [x] **전략 조회**: Helius DAS `getAssetsByOwner` → 내 전략 cNFT 목록
- [x] **신호 히스토리**: Helius DAS `getAssetsByGroup` → 전략별 신호 리프 목록
- [x] **무결성 검증**: `getAssetProof` → Merkle proof 검증
  - DB 신호 해시 vs 온체인 리프 해시 비교
  - 불일치 시 → 조작 감지 경고
- [x] **선택적 공개**: 소유자가 원본 공개 → 해시 일치 검증 가능

### 5.5 API 엔드포인트

- [x] `POST /blockchain/strategy/mint` — 전략을 cNFT로 민팅
- [x] `POST /blockchain/strategy/{id}/burn` — 전략 cNFT 삭제 (소유자만)
- [x] `GET /blockchain/strategy/{id}/verify` — 전략 무결성 검증 (DB vs 온체인 해시)
- [x] `POST /blockchain/signal` — 매매 신호 압축 기록 (자동 호출)
- [x] `GET /blockchain/signal/history/{strategy_id}` — 신호 히스토리 조회 (DAS API)
- [x] `GET /blockchain/signal/{id}/proof` — 개별 신호 Merkle proof 검증

### 5.6 프론트엔드 UI

- [x] 전략 상세 페이지에 "Mint as NFT" 버튼
- [x] 온체인 등록 전략에 "Verified on Solana" 배지
- [x] 신호 히스토리 탭 (온체인 기록 목록 + Merkle proof 상태)
- [x] 전략 공개/비공개 토글 (원본 공개 시 검증 가능)

### 5.7 기술 스택

| 라이브러리 | 용도 |
|-----------|------|
| `@solana/spl-account-compression` | Merkle Tree 생성/관리 |
| `@metaplex-foundation/mpl-bubblegum` | cNFT 민팅/burn |
| `Helius DAS API` | 압축 데이터 인덱싱/조회/proof |
| `Arweave` 또는 `IPFS (Pinata)` | 전략 원본 영구 저장 |
| `@solana/web3.js` | Solana 트랜잭션 |

### 5.8 비용 추정

| 항목 | 비용 | 빈도 |
|------|------|------|
| Merkle Tree 생성 | ~$0.05 | 1회 |
| 전략 cNFT 민팅 | ~$0.00005 | 전략당 |
| 매매 신호 기록 | ~$0.00001 | 신호당 |
| Helius DAS 조회 | 무료 | 무제한 |
| Arweave 저장 | ~$0.001/KB | 전략당 |
| **100명 유저 × 100전략 × 10만 신호** | **~$2** | **총** |

### 5.9 DB 스키마 추가

```sql
-- 온체인 전략 (cNFT)
CREATE TABLE onchain_strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  asset_id VARCHAR(44) NOT NULL,      -- cNFT asset ID
  merkle_tree VARCHAR(44) NOT NULL,   -- Merkle Tree address
  strategy_hash VARCHAR(64) NOT NULL, -- SHA256 of strategy JSON
  arweave_uri TEXT,                    -- Arweave/IPFS URI for full JSON
  is_public BOOLEAN DEFAULT FALSE,    -- 원본 공개 여부
  registered_at TIMESTAMPTZ DEFAULT NOW()
);

-- 온체인 매매 신호 (로컬 캐시, 원본은 Helius DAS)
CREATE TABLE onchain_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  leaf_index INTEGER NOT NULL,        -- Merkle Tree leaf index
  signal_hash VARCHAR(64) NOT NULL,   -- SHA256 of signal data
  signal_type TEXT NOT NULL,           -- 'long_entry' | 'short_entry' | 'close'
  symbol VARCHAR(20),
  price DECIMAL,
  leverage INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.10 향후 확장: 전략 마켓플레이스

```
전략 소유자 → cNFT 공개 + 신호 히스토리 공개
                    ↓
누구나 검증 (Merkle proof)
                    ↓
검증된 전략 → 구독/카피트레이딩
                    ↓
수익 발생 시 로열티 (Metaplex Creator Royalty)
```

이 구조가 Pricing의 **"Web3 Native" 플랜**의 기술적 기반.

---

## 일정 요약

| Phase | 내용 | 기간 | 의존성 | 상태 |
|-------|------|------|--------|------|
| **Phase 1** | 선물 백테스트 엔진 전환 | 5일 | 없음 | **완료** |
| **Phase 2** | 최적화 + Walk-Forward | 5일 | Phase 1 | **완료** |
| **Phase 3** | 실시간 + 모의투자 | 7일 | Phase 1 | **완료** |
| ~~Phase 4~~ | ~~Rust 고속 브릿지~~ | ~~5일~~ | - | **보류** (Python 속도 충분) |
| **Phase 5** | 블록체인 통합 (상태 압축) | 7일 | Phase 3 | **구조 완료** (시뮬레이션 모드, Solana SDK 설치 후 활성화) |
| **총 예상** | Phase 1~3 + 5 | **~24일** | | Python only, 서버 1개 |

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

---

## 프론트엔드 UI/UX 계획

### 현재 컴포넌트 구조 (33개 TSX 파일)

```
frontend/
├── app/
│   ├── page.tsx                    (랜딩)
│   ├── layout.tsx                  (루트 레이아웃)
│   ├── chat/page.tsx               (AI 채팅)
│   └── strategies/
│       ├── page.tsx                (전략 목록)
│       └── [id]/page.tsx           (전략 상세)
├── components/
│   ├── chat/                       (채팅 관련 8개)
│   ├── common/                     (공통 6개)
│   ├── landing/                    (랜딩 7개)
│   ├── layout/                     (레이아웃 2개)
│   ├── market/                     (시장 1개)
│   └── wallet/                     (지갑 3개)
├── stores/
│   ├── chatStore.ts
│   ├── authStore.ts
│   └── languageStore.ts
└── lib/
    ├── api.ts
    ├── i18n.ts
    └── types.ts
```

### Phase 1 프론트엔드 변경

#### 수정할 컴포넌트

| 컴포넌트 | 변경 내용 |
|---------|----------|
| `StrategyCard.tsx` | 레버리지 입력 (1~125x 슬라이더), 방향 선택 (Long/Short/Both 라디오), 분할익절/추적손절 토글 |
| `BacktestResult.tsx` | 확장 메트릭 표시 (CAGR, Profit Factor, Calmar Ratio), Long/Short 별도 승률 |
| `BacktestChart.tsx` | 롱/숏 진입점 마커 색상 구분 (녹색/빨간색) |
| `BacktestSummary.tsx` | AI 리포트에 선물 리스크 코멘트 표시 |
| `types.ts` | `ParsedStrategy` 타입에 `leverage`, `direction`, `partial_exit`, `trailing_stop` 추가 |

#### 신규 컴포넌트 없음 (기존 컴포넌트 확장만)

#### UX 플로우
```
사용자 → 채팅에서 전략 생성
     → StrategyCard에 레버리지/방향 설정 UI 추가됨
     → "Run Backtest" 클릭 → 선물 메트릭 포함 결과 표시
     → AI 리포트에 "레버리지 10x → 강제청산 가격 $XX,XXX" 포함
```

### Phase 2 프론트엔드 변경

#### 수정할 컴포넌트

| 컴포넌트 | 변경 내용 |
|---------|----------|
| `strategies/[id]/page.tsx` | "Optimize" 버튼 + "Walk-Forward" 버튼 추가 |

#### 신규 컴포넌트

| 컴포넌트 | 위치 | 설명 |
|---------|------|------|
| `OptimizeModal.tsx` | `components/strategy/` | 파라미터 범위 입력 폼 + 결과 테이블 |
| `OptimizeResults.tsx` | `components/strategy/` | 상위 10개 파라미터 조합 테이블 (정렬/선택 가능) |
| `WalkForwardChart.tsx` | `components/strategy/` | IS/OOS 수익률 비교 바 차트 (4윈도우) |
| `WalkForwardResult.tsx` | `components/strategy/` | 과적합 판정 배지 (Pass/Fail) + 윈도우별 상세 |

#### OptimizeModal 레이아웃
```
┌─────────────────────────────────────┐
│ Optimize Strategy                    │
│                                      │
│ Parameter Ranges:                    │
│ ┌──────────┬───────────────────┐    │
│ │ RSI Period│ [10] [14] [20]    │    │
│ │ TP (%)    │ [1.0] [1.5] [2.0] │    │
│ │ SL (%)    │ [-0.3] [-0.4] [-0.5]│  │
│ │ Leverage  │ [5] [10] [20]     │    │
│ └──────────┴───────────────────┘    │
│                                      │
│ Objective: [Sharpe ▼]               │
│ Max Combinations: [100]              │
│                                      │
│ [Cancel]          [Run Optimization] │
└─────────────────────────────────────┘
         ↓ 완료 후
┌─────────────────────────────────────┐
│ Top 10 Results                       │
│ ┌────┬─────┬────┬────┬──────┬────┐ │
│ │Rank│RSI  │TP  │SL  │Sharpe│Apply│ │
│ │ 1  │ 14  │1.5 │-0.4│ 2.1  │ [✓]│ │
│ │ 2  │ 20  │2.0 │-0.3│ 1.8  │ [ ]│ │
│ │ ...│     │    │    │      │    │ │
│ └────┴─────┴────┴────┴──────┴────┘ │
│                    [Apply Selected]  │
└─────────────────────────────────────┘
```

#### WalkForward 차트 레이아웃
```
┌─────────────────────────────────────┐
│ Walk-Forward Analysis    [Pass ✅]   │
│                                      │
│ IS Return  ████████████ 47%          │
│ OOS Return ███████      28% (60%)    │
│                                      │
│ Window 1: IS 45% → OOS 27% ✅       │
│ Window 2: IS 52% → OOS 31% ✅       │
│ Window 3: IS 43% → OOS 25% ✅       │
│ Window 4: IS 48% → OOS 29% ✅       │
│                                      │
│ Avg OOS/IS Ratio: 60% (≥50% = Pass) │
└─────────────────────────────────────┘
```

#### 로딩 UX
- 최적화 실행 중: 프로그레스 바 + "Testing 45/100 combinations..." 텍스트
- Walk-Forward 실행 중: "Analyzing Window 2/4..." 단계별 진행

### Phase 3 프론트엔드 변경

#### 신규 페이지

`app/trading/page.tsx` — 모의투자 대시보드

#### 신규 컴포넌트

| 컴포넌트 | 위치 | 설명 |
|---------|------|------|
| `TradingDashboard.tsx` | `components/trading/` | 메인 레이아웃 (차트 + 포지션 + 히스토리) |
| `LiveChart.tsx` | `components/trading/` | lightweight-charts WebSocket 실시간 가격 차트 |
| `PositionCard.tsx` | `components/trading/` | 현재 포지션 (Long/Short, 진입가, PnL, 레버리지) |
| `BalanceCard.tsx` | `components/trading/` | 잔고/마진/미실현PnL 표시 |
| `DemoTradeLog.tsx` | `components/trading/` | 실시간 거래 히스토리 테이블 |
| `DemoControls.tsx` | `components/trading/` | 시작/중지 버튼 + 전략/심볼/레버리지 선택 |
| `SignalIndicator.tsx` | `components/trading/` | 매수/매도/대기 신호 실시간 표시 |

#### 수정할 컴포넌트

| 컴포넌트 | 변경 내용 |
|---------|----------|
| `Navigation.tsx` | "Trading" 네비 링크 추가 |
| `layout.tsx` | /trading 경로 메타데이터 |

#### 모의투자 대시보드 레이아웃
```
┌────────────────────────────────────────────────────┐
│ Header: TradeCoach AI │ Chat │ Strategies │ Trading │
├────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────┐ ┌───────────┐│
│ │                                  │ │ Position  ││
│ │     Live Price Chart             │ │ LONG BTC  ││
│ │     (lightweight-charts)         │ │ @65,200   ││
│ │     + 진입/청산 마커             │ │ PnL +$32  ││
│ │                                  │ │ Lev: 10x  ││
│ │                                  │ ├───────────┤│
│ │                                  │ │ Balance   ││
│ │                                  │ │ $1,247    ││
│ │                                  │ │ Margin $50││
│ └──────────────────────────────────┘ └───────────┘│
│ ┌──────────────────────┐ ┌────────────────────────┐│
│ │ Controls             │ │ Trade Log              ││
│ │ Strategy: [DDIF ▼]   │ │ #23 LONG  +$12  +1.2% ││
│ │ Symbol:   [BTCUSDT ▼]│ │ #22 SHORT -$5   -0.5% ││
│ │ Leverage: [10x]      │ │ #21 LONG  +$28  +2.8% ││
│ │ [▶ Start] [■ Stop]   │ │ ...                    ││
│ └──────────────────────┘ └────────────────────────┘│
└────────────────────────────────────────────────────┘
```

#### 모바일 레이아웃
```
┌──────────────────┐
│ Trading          │
├──────────────────┤
│ Live Chart       │
│ (전체 너비)      │
├──────────────────┤
│ Position | Balance│
│ (2열 그리드)     │
├──────────────────┤
│ Signal: 🟢 LONG  │
├──────────────────┤
│ Controls         │
│ [▶ Start] [■ Stop]│
├──────────────────┤
│ Trade Log (스크롤)│
└──────────────────┘
```

#### 실시간 업데이트 방식
- **가격 차트**: WebSocket (`/ws/price/{symbol}`) → 100ms 간격 업데이트
- **포지션/잔고**: 2초 폴링 (`GET /trading/demo/status`)
- **거래 로그**: 포지션 변경 시에만 리페치

### Phase 5 프론트엔드 변경

#### 수정할 컴포넌트

| 컴포넌트 | 변경 내용 |
|---------|----------|
| `strategies/[id]/page.tsx` | "Mint as NFT" 버튼 + "Verified ✅" 배지 |
| `StrategyCard.tsx` | 온체인 등록 상태 아이콘 (🔗 체인 아이콘) |

#### 신규 컴포넌트

| 컴포넌트 | 위치 | 설명 |
|---------|------|------|
| `MintModal.tsx` | `components/blockchain/` | cNFT 민팅 확인 모달 (전략 해시 표시 + 비용 안내) |
| `OnchainBadge.tsx` | `components/blockchain/` | "Verified on Solana" 배지 (Merkle proof 상태) |
| `SignalHistory.tsx` | `components/blockchain/` | 온체인 신호 히스토리 탭 (DAS API 조회 결과) |
| `VerifyButton.tsx` | `components/blockchain/` | 무결성 검증 버튼 (DB vs 온체인 해시 비교) |

#### i18n 번역 추가

각 Phase에서 신규 UI 텍스트를 `lib/i18n.ts`에 추가:
- Phase 1: ~15키 (레버리지, 방향, 분할익절 관련)
- Phase 2: ~25키 (최적화 모달, Walk-Forward 결과)
- Phase 3: ~30키 (모의투자 대시보드 전체)
- Phase 5: ~15키 (블록체인 민팅, 검증, 신호 히스토리)

### 컴포넌트 변경 요약

| Phase | 수정 | 신규 | 합계 |
|-------|------|------|------|
| Phase 1 | 5개 | 0개 | 5개 |
| Phase 2 | 1개 | 4개 | 5개 |
| Phase 3 | 2개 | 7개 (+1 page) | 10개 |
| Phase 5 | 2개 | 4개 + 마켓플레이스 5개 | 11개 |
| **합계** | **10개** | **20개** | **31개** |

---

## 전체 페이지 맵

### 통합 후 최종 페이지 구조 (7개)

```
/                     ← 랜딩 (변경 없음)
/chat                 ← AI 채팅 (Phase 1: 선물 UI 확장)
/strategies           ← 전략 목록 (변경 없음)
/strategies/[id]      ← 전략 상세 (Phase 1+2+5: 확장 메트릭, 최적화, NFT)
/trading              ← 모의투자 대시보드 (Phase 3: 신규)
/marketplace          ← 전략 마켓플레이스 (Phase 5: 신규)
/marketplace/[id]     ← 마켓플레이스 전략 상세 (Phase 5: 신규)
```

### 마켓플레이스 페이지 (Phase 5 확장)

#### `/marketplace` — 공개 전략 목록

```
┌──────────────────────────────────────────────────┐
│ Strategy Marketplace              [Filter ▼] [Sort ▼]│
├──────────────────────────────────────────────────┤
│ ┌────────────┐ ┌────────────┐ ┌────────────┐     │
│ │ DDIF v3    │ │ RSI Bounce │ │ EMA Cross  │     │
│ │ BTCUSDT    │ │ ETHUSDT    │ │ SOLUSDT    │     │
│ │ Verified ✅│ │ Verified ✅│ │ Pending ⏳ │     │
│ │ +47% / 3mo │ │ +28% / 2mo │ │ +12% / 1mo │     │
│ │ MDD -12%   │ │ MDD -8%    │ │ MDD -15%   │     │
│ │ 147 signals│ │ 89 signals │ │ 34 signals │     │
│ │ by @kim    │ │ by @park   │ │ by @lee    │     │
│ └────────────┘ └────────────┘ └────────────┘     │
└──────────────────────────────────────────────────┘
```

#### `/marketplace/[id]` — 전략 상세 (성과만 공개, 내용 비공개)

```
┌──────────────────────────────────────────────────┐
│ DDIF Strategy v3                    Verified ✅    │
│ BTCUSDT · 15m/3m · by @trader_kim                 │
│                                                    │
│ Verified Performance (on-chain proof)              │
│ ├── Return: +47.2%  │  MDD: -12.3%               │
│ ├── Sharpe: 2.1     │  Win Rate: 62%             │
│ └── Signals: 147 recorded on Solana               │
│                                                    │
│ Signal Timeline (verified, not editable)           │
│ ├── 03/15 14:30  LONG   ████ +2.3%               │
│ ├── 03/16 09:15  SHORT  ██   -0.5%               │
│ └── 03/17 11:00  LONG   ██████ +4.1%             │
│                                                    │
│ Strategy Details: 🔒 Hidden                        │
│ (Content hash verified on Solana. Only the owner  │
│  can reveal strategy parameters.)                  │
│                                                    │
│ [Import Performance Summary]  [Subscribe $9.99/mo] │
└──────────────────────────────────────────────────┘
```

#### 마켓플레이스 신규 컴포넌트

| 컴포넌트 | 위치 | 설명 |
|---------|------|------|
| `MarketplaceGrid.tsx` | `components/marketplace/` | 공개 전략 카드 그리드 + 필터/정렬 |
| `MarketplaceCard.tsx` | `components/marketplace/` | 개별 전략 카드 (수익률, 배지, 신호 수) |
| `VerifiedPerformance.tsx` | `components/marketplace/` | 온체인 검증 성과 표시 |
| `SignalTimeline.tsx` | `components/marketplace/` | 매매 신호 타임라인 차트 |
| `PrivacyBadge.tsx` | `components/marketplace/` | "🔒 Hidden" / "🔓 Public" 전략 공개 상태 |

---

## 전략 프라이버시 모델

### 해시 기반 공개/비공개 설계

| 항목 | 온체인 (공개) | 오프체인 (비공개) |
|------|------------|----------------|
| 전략 해시 (SHA256) | ✅ | - |
| 전략 이름/심볼 | ✅ (메타데이터) | - |
| **진입 조건 (RSI, MACD 등)** | **해시만** | **소유자만 보유** |
| **파라미터 (period, threshold)** | **해시만** | **소유자만 보유** |
| **TP/SL/레버리지** | **해시만** | **소유자만 보유** |
| 신호 타입 (Long/Short/Close) | ✅ | - |
| 신호 시간 | ✅ | - |
| 신호 가격 | 해시만 (선택) | 소유자 선택 |

### 공개 수준 옵션 (소유자가 선택)

```
Level 1: 기본 (최소 공개)
  → 이름, 심볼, 검증 수익률, 신호 수만

Level 2: 신호 공개
  → Level 1 + 신호 시간/타입/가격 공개

Level 3: 전략 공개 (향후)
  → Level 2 + 전략 원본 JSON 공개 (Arweave URI 공유)
```

---

## AI 프롬프트 통합 계획

### Phase별 프롬프트 변경

| Phase | 변경 파일 | 추가 내용 |
|-------|---------|----------|
| **1** | `coaching.py` | 선물 리스크 프레임워크 (레버리지 경고, 강제청산 교육) |
| **1** | `backtest_report.py` | 확장 메트릭 해석 기준 (CAGR, Profit Factor, Calmar) |
| **1** | `strategy_parser.py` | 선물 전용 필드 파싱 (leverage, direction, partial_exit) |
| **2** | `coaching.py` | 최적화/Walk-Forward 결과 해석 컨텍스트 |
| **3** | `coaching.py` | 모의투자 실시간 성과 분석 컨텍스트 |
| **5** | `coaching.py` | 온체인 검증 상태 표시 |

### 컨텍스트 주입 방식
- **직접 주입** (RAG 아님): 총 ~7,300 토큰 (Gemini 한도 100만 대비 0.73%)
- Phase 1~5 추가분: ~800 토큰 추가
- 기존 RAG: 트레이딩 지식 30개 문서 (키워드 매칭 검색, 유지)

---

## RAG 지식 베이스 확장 계획

### Phase 1에서 추가할 트레이딩 지식 문서

| 원본 (RCoinFutTrader) | → RAG 문서 | 카테고리 |
|---------------------|----------|---------|
| `strategy/logic.rs` DDIF 로직 | "DDIF 전략: 멀티타임프레임 ADX/DI 기반 매매" | strategy |
| `backtester/metrics.rs` | "Calmar Ratio, Profit Factor 해석 기준" | backtest |
| `config.toml` 리스크 설정 | "선물 리스크 관리: 분할익절, 추적손절 실전 가이드" | risk |
| Walk-Forward 로직 | "인샘플/아웃오브샘플 최적화 실전 가이드" | optimization |
| 레버리지 관리 | "선물 레버리지 위험: 강제청산 메커니즘 이해" | risk |

→ `backend/data/trading_knowledge.json`에 5개 문서 추가 (30개 → 35개)

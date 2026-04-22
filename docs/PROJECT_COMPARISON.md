# TradeCoach-AI vs StrategyVault vs BinanceTrader — 종합 비교 분석

> 작성일: 2026-03-20

---

## 1. 아키텍처 비교

| 항목 | TradeCoach-AI (내 프로젝트) | StrategyVault | BinanceTrader |
|------|--------------------------|---------------|---------------|
| **프론트엔드** | Next.js 15 + Tailwind v4 | Next.js 16 + Tailwind v4 | React 18 + Vite + Tailwind v3 |
| **백엔드** | FastAPI (Python) | Express (TypeScript) | FastAPI (Python) |
| **DB** | Supabase (PostgreSQL) | Solana On-chain (PDA) | PostgreSQL + Redis + Celery |
| **AI 모델** | Gemini 3.1 Pro | 없음 | Claude + GPT-4o (듀얼) |
| **블록체인** | Solana (cNFT, 해시 기반) | Solana (Anchor 4 programs) | Solana (StrategyVault 연동) |
| **실시간 데이터** | Binance REST 폴링 (3초) | Pyth Oracle (실시간) | Binance WebSocket (틱 단위) |
| **인증** | Phantom 지갑 + JWT | Phantom + TX 서명 | JWT + bcrypt (이메일) |

---

## 2. 기능별 상세 비교

### 2.1 전략 생성

| 기능 | TradeCoach-AI | StrategyVault | BinanceTrader |
|------|-------------|---------------|---------------|
| 자연어 → 전략 | ✅ Gemini (JSON 구조체) | ❌ (수동 등록) | ✅ Claude/GPT (Python 코드) |
| 차트 이미지 분석 | ✅ Gemini 멀티모달 | ❌ | ✅ Claude/GPT 비전 |
| 대화형 수정 | ✅ 채팅 기반 | ❌ | ✅ 대화 이력 기반 |
| **전략 포맷** | **JSON 구조체** | 백테스트 메트릭만 | **Python 코드 (함수)** |

### 2.2 기술 지표

| 지표 | TradeCoach-AI | StrategyVault | BinanceTrader |
|------|-------------|---------------|---------------|
| 지표 수 | **~12개** | N/A (외부 백테스트) | **37개** |
| RSI | ✅ | - | ✅ |
| MACD | ✅ | - | ✅ (MACD + HIST + SIGNAL) |
| Bollinger Bands | ✅ (상/하) | - | ✅ (상/중/하) |
| EMA/SMA | ✅ (2-3개) | - | ✅ (9개: EMA 5/10/20/60/120, SMA 5/10/20/60) |
| Stochastic | ✅ (Stoch RSI) | - | ✅ (K/D + Fast K/D) |
| ATR | ✅ | - | ✅ |
| ADX/DI | ❌ | - | ✅ |
| SAR (Parabolic) | ❌ | - | ✅ |
| CCI | ❌ | - | ✅ |
| MFI | ❌ | - | ✅ |
| OBV | ❌ | - | ✅ |
| VWAP | ✅ | - | ❌ |
| Williams %R | ❌ | - | ✅ |
| Aroon | ❌ | - | ✅ |
| ROC/Momentum | ❌ | - | ✅ |

> **핵심 갭**: TradeCoach-AI는 12개, BinanceTrader는 37개. **ADX, SAR, CCI, MFI, OBV, Williams %R, Aroon, ROC** 등이 누락.

### 2.3 백테스트 엔진

| 기능 | TradeCoach-AI | StrategyVault | BinanceTrader |
|------|-------------|---------------|---------------|
| 자체 엔진 | ✅ (Futures 전용) | ❌ (외부 도구 사용) | ✅ (커스텀) |
| 레버리지 | ✅ (1-125x) | 기록만 (1-125x) | ✅ (1-125x) |
| 청산 시뮬레이션 | ✅ | ❌ | ❌ (미구현) |
| 슬리피지 | ❌ **누락** | N/A | ✅ (0.01% 고정) |
| 수수료 | ✅ (0.04% × 2) | N/A | ✅ (0.04% × 2) |
| 부분 익절 | ✅ | N/A | ❌ |
| 트레일링 스탑 | ✅ | N/A | ❌ |
| 포지션 사이징 | ✅ (fixed) | N/A | ❌ (전액 투입) |
| **IS/OOS 검증** | ❌ **누락** | N/A | ✅ (과적합 점수) |
| Walk-Forward | ✅ (코드 있음, 미연동) | N/A | ❌ |
| Sharpe | ✅ | N/A | ✅ |
| Calmar | ✅ | N/A | ❌ |
| CAGR | ❌ **누락** | N/A | ✅ |

### 2.4 파라미터 최적화

| 기능 | TradeCoach-AI | StrategyVault | BinanceTrader |
|------|-------------|---------------|---------------|
| Grid Search | ✅ (병렬) | ❌ | ❌ |
| 복합 목적 함수 | ✅ (Sharpe 50%+Calmar 30%+PF 20%) | ❌ | ❌ |
| 인디케이터 파라미터 | ✅ (방금 추가) | ❌ | ❌ |
| 유전 알고리즘 | ❌ | ❌ | ❌ |

### 2.5 모의투자 (Paper Trading)

| 기능 | TradeCoach-AI | StrategyVault | BinanceTrader |
|------|-------------|---------------|---------------|
| 실시간 가격 | ✅ (Binance REST 3초 폴링) | ✅ (Pyth Oracle) | ✅ (**WebSocket 틱 단위**) |
| 캔들 생성 | ❌ (히스토리 100개 로드) | N/A | ✅ (aggTrade → 1분봉 실시간 생성) |
| 자동 신호 평가 | ✅ | ✅ (수동 기록) | ✅ |
| P&L 실시간 | ✅ | ✅ (온체인) | ✅ |
| **실거래 모드** | ❌ **없음** | ✅ (Live 모드) | ✅ (**Binance 실주문**) |
| 세션 저장 | ❌ (인메모리) | ✅ (온체인 영구) | ✅ (PostgreSQL) |

> **핵심 갭**: TradeCoach-AI는 REST 폴링(3초)만 지원. BinanceTrader는 WebSocket aggTrade 틱 단위 + 캔들 실시간 생성.

### 2.6 블록체인 통합

| 기능 | TradeCoach-AI | StrategyVault | BinanceTrader |
|------|-------------|---------------|---------------|
| 전략 등록 | ✅ (cNFT 해시) | ✅ (**Anchor PDA, 불변**) | ✅ (StrategyVault 연동) |
| 신호 기록 | ✅ (SHA256 버퍼 → 배치) | ✅ (**실시간 PDA, 불변**) | ✅ (StrategyVault Gateway) |
| **이중 가격 검증** | ❌ **누락** | ✅ (**Pyth Oracle + 거래소 가격**) | ❌ |
| **성능 검증** | ❌ **누락** | ✅ (3+명 독립 검증 → Verified 배지) | ❌ |
| 마켓플레이스 | ❌ (계획만) | ✅ (**구매 + 렌탈 + 에스크로**) | ❌ |
| 수익 정산 | ❌ | ✅ (95:5 분배, 일일 정산) | ❌ |
| 랭킹 시스템 | ❌ | ✅ (카테고리별 Top 100) | ❌ |

> **핵심 갭**: StrategyVault의 블록체인 통합은 훨씬 성숙함. Pyth Oracle 이중 가격 검증, 독립 검증 시스템, 마켓플레이스가 모두 구현됨.

### 2.7 AI 프롬프트 비교

| 항목 | TradeCoach-AI | BinanceTrader |
|------|-------------|---------------|
| **전략 파싱 출력** | JSON 구조체 (선언적) | Python 코드 (buy_condition/sell_condition 함수) |
| **보안 검증** | ❌ 없음 (JSON이므로 불필요) | ✅ **16개 위험 키워드 차단 + 화이트리스트 샌드박스** |
| 지표 문서화 | ~12개 | **37개 (전체 나열)** |
| **레버리지별 TP/SL** | ✅ 테이블 제공 | ❌ (사용자 결정) |
| **옵티마이저 호환 기본값** | ✅ (방금 추가) | ❌ |
| **결과 분석 프롬프트** | ✅ (coaching.py) | ✅ (result_analyzer.py) |
| **이미지 분석 가이드** | ✅ (6단계) | ✅ (차트 → 코드) |
| **대화 이력 유지** | ✅ | ✅ |
| **교육적 프레임워크** | ✅ (1-2% 규칙, 리스크 우선) | ❌ |

### 2.8 시그널 디스패치

| 채널 | TradeCoach-AI | StrategyVault | BinanceTrader |
|------|-------------|---------------|---------------|
| Webhook | ❌ | ✅ (Gateway API) | ✅ (HMAC-SHA256) |
| Telegram | ❌ | ❌ | ✅ |
| Discord | ❌ | ❌ | ✅ |
| 블록체인 | ✅ (Solana) | ✅ (Solana) | ✅ (StrategyVault) |
| **멀티채널 동시 발송** | ❌ | ❌ | ✅ (병렬 + 재시도) |

---

## 3. TradeCoach-AI에 부족한 부분 — 우선순위별 정리

### 🔴 Critical (반드시 추가)

#### 3.1 기술 지표 확장 (12 → 37개)
**BinanceTrader에서 가져올 지표:**
- **추세**: ADX, DI_PLUS, DI_MINUS, SAR (Parabolic), AROON_UP/DOWN
- **모멘텀**: CCI, MOM, ROC, WILLR (Williams %R), MFI, APO, PPO
- **거래량**: OBV, AD (Accumulation/Distribution), ADOSC
- **추가 이동평균**: EMA 60/120, SMA 60

**영향**: strategy_parser.py 프롬프트 + 백테스트 엔진의 signal_evaluator + 프론트엔드 UI 모두 수정 필요.

#### 3.2 IS/OOS (In-Sample/Out-of-Sample) 과적합 검증
**BinanceTrader 방식 채택:**
```
데이터 분할: 2/3 (In-Sample) + 1/3 (Out-of-Sample)
과적합 점수: 1 - (OOS_Return / IS_Return)  → 0~1 (높을수록 과적합)
Win Rate 저하: IS_WinRate - OOS_WinRate

판정:
  ≥50% OOS/IS → ✅ SAFE
  25-50%      → ⚠️ CAUTIOUS
  10-25%      → ⛔ RISKY
  <10%        → 🚫 REJECT
```
> `walk_forward.py`가 이미 있지만 백테스트 파이프라인에 미연동. IS/OOS를 백테스트 기본 옵션으로 추가해야 함.

#### 3.3 슬리피지 시뮬레이션
- **현재**: 슬리피지 0 (비현실적)
- **BinanceTrader**: 0.01% 고정 슬리피지
- **추천**: `FuturesConfig`에 `slippage_pct: float = 0.01` 추가, 진입/퇴장 가격에 적용

#### 3.4 WebSocket 실시간 가격 (데모 트레이딩)
- **현재**: REST 폴링 3초 간격
- **BinanceTrader**: `aggTrade` WebSocket → 1분봉 실시간 생성 (`CandleManager`)
- **추천**: `demo_price_feed.py`를 WebSocket 기반으로 교체. `binance_ws.py`는 이미 있으나 차트용으로만 사용 중.

### 🟡 Important (강하게 권장)

#### 3.5 Pyth Oracle 이중 가격 검증 (StrategyVault)
- **현재**: 거래소 가격만 기록
- **StrategyVault**: 거래소 가격 + Pyth Oracle 가격 동시 기록 + 델타 계산
- **추천**: 신호 기록 시 Pyth Hermes API에서 가격도 받아서 `price_delta_bps` 계산

#### 3.6 CAGR (연평균 성장률) 메트릭 추가
- **현재**: Total Return, Sharpe, Calmar, Profit Factor, Win Rate
- **BinanceTrader**: + **CAGR** (연간 복리 수익률)
- **추천**: `metrics.py`에 `cagr = ((final/initial)^(365/days) - 1) * 100` 추가

#### 3.7 전략 코드 보안 샌드박스 (BinanceTrader 패턴)
- **현재**: JSON 구조체라 코드 인젝션 위험 낮음
- **그러나**: 향후 커스텀 지표/전략 로직 지원 시 필수
- **BinanceTrader 방식**: 16개 위험 키워드 차단 + 8개 허용 빌트인만 namespace에 노출

#### 3.8 멀티채널 시그널 디스패치
- **현재**: 블록체인만 (Solana signal_recorder)
- **BinanceTrader**: Webhook + Telegram + Discord + Blockchain (병렬 + 3회 재시도)
- **추천**: 최소 Telegram/Discord 알림 채널 추가 (거래 진입/퇴장 알림)

#### 3.9 모의투자 세션 DB 저장
- **현재**: 인메모리 (`_active_sessions` dict)
- **BinanceTrader**: PostgreSQL Trade 테이블에 영구 저장
- **추천**: Supabase `demo_sessions` + `demo_trades` 테이블에 저장

### 🟢 Recommended (시간 될 때)

#### 3.10 성능 검증 + 독립 검증 시스템 (StrategyVault)
- 100+ 신호, 90일+ 트랙 레코드, 주 2회+ 신호 → "Verified" 배지
- 3명 이상 독립 검증자 → 승격
- 현재 TradeCoach-AI는 NFT 민팅만으로 "Verified" → 기준이 너무 느슨

#### 3.11 마켓플레이스 에스크로 + 일일 정산 (StrategyVault)
- 전략 구매: 95:5 (소유자:플랫폼)
- 렌탈: 에스크로 PDA에 SOL 예치 → 일일 정산 (permissionless crank)
- 만료 시 자동 환불

#### 3.12 랭킹 시스템
- 카테고리별 (수익률, 승률, Sharpe, MDD)
- 페이지네이션 (Top 100)
- 마켓플레이스 검색/필터와 연동

---

## 4. AI 프롬프트에 추가해야 할 내용

### 4.1 `strategy_parser.py` 추가 사항

```
1. 누락 지표 추가 (ADX, SAR, CCI, MFI, OBV, Williams %R, Aroon, ROC, MOM)
   → "지원 지표" 섹션에 25개+ 지표 문서화

2. 복합 조건 패턴 예시 추가:
   - 추세 확인: "MA 정배열 + RSI > 50 + ADX > 25"
   - 평균회귀: "Bollinger 하단 + RSI < 30 + 거래량 급증"
   - 모멘텀: "MACD 골든크로스 + OBV 상승 + ATR 높음"

3. 과적합 경고 문구:
   "5개 이상의 조건을 AND로 결합하면 과적합 위험이 높아집니다.
    2-3개 핵심 조건 + 1-2개 필터로 구성하는 것을 권장합니다."

4. 포지션 사이징 가이드:
   "max_positions 2 이상일 때 분산 투자 효과를 얻을 수 있지만,
    총 노출 = positions × leverage 가 포트폴리오의 50%를 넘지 않도록 해야 합니다."
```

### 4.2 `coaching.py` 추가 사항

```
1. IS/OOS 검증 안내:
   "백테스트 결과가 좋더라도 과적합일 수 있습니다.
    IS/OOS 검증을 실행하여 OOS/IS 비율이 50% 이상인지 확인하세요."

2. 과적합 점수 해석 가이드:
   0-0.5: ✅ 안전 (OOS 성능이 IS의 50%+ 유지)
   0.5-0.75: ⚠️ 주의 (조건 수를 줄이거나 기간을 변경해보세요)
   0.75+: ⛔ 과적합 (전략 재설계 필요)

3. 슬리피지/실행 비용 안내:
   "실제 거래에서는 0.01-0.05% 슬리피지가 발생합니다.
    백테스트 수익률에서 거래당 0.01%를 추가 차감하여 계산하세요."

4. 다중 시간프레임 분석 제안:
   "1시간봉으로 진입 시점을 잡고, 4시간봉으로 추세를 확인하면
    신호의 신뢰도가 높아집니다."
```

---

## 5. 통합 아키텍처 제안

StrategyVault와 BinanceTrader의 장점을 TradeCoach-AI에 통합하는 방향:

```
TradeCoach-AI (현재)
├── AI 전략 생성 (Gemini) ✅
├── 백테스트 엔진 ✅ (+슬리피지, +IS/OOS, +CAGR)
├── 파라미터 최적화 ✅
├── 모의투자 ✅ (+WebSocket 업그레이드)
├── cNFT 민팅 ✅

+ StrategyVault 통합
├── Pyth Oracle 이중 가격 검증 (신뢰도 강화)
├── 독립 검증 시스템 (100+ 신호 → Verified)
├── 마켓플레이스 에스크로 (구매 + 렌탈)
├── 랭킹 시스템 (수익률/Sharpe/승률별)

+ BinanceTrader 통합
├── 37개 기술 지표 (ADX, SAR, CCI, MFI, OBV 등)
├── IS/OOS 과적합 검증 (점수화)
├── WebSocket 실시간 데이터 (aggTrade)
├── 멀티채널 알림 (Telegram, Discord, Webhook)
├── 실거래 모드 (Binance API 직접 주문)
├── 코드 보안 샌드박스 (미래 커스텀 전략용)
```

---

## 6. 즉시 실행 가능한 액션 아이템

| 우선순위 | 작업 | 예상 범위 |
|---------|------|---------|
| 🔴 1 | 기술 지표 25개 추가 (indicators 파일 + 프롬프트) | 중 |
| 🔴 2 | IS/OOS 과적합 검증 백테스트에 통합 | 중 |
| 🔴 3 | 슬리피지 시뮬레이션 (engine.py에 0.01% 추가) | 소 |
| 🔴 4 | WebSocket 가격 피드 (demo_price_feed 업그레이드) | 중 |
| 🟡 5 | CAGR 메트릭 추가 | 소 |
| 🟡 6 | Pyth Oracle 이중 가격 검증 | 중 |
| 🟡 7 | Telegram/Discord 알림 채널 | 중 |
| 🟡 8 | 모의투자 세션 DB 저장 (Supabase) | 중 |
| 🟢 9 | 독립 검증 시스템 (StrategyVault 패턴) | 대 |
| 🟢 10 | 마켓플레이스 에스크로 | 대 |

---

## 7. 설계문서 기반 추가 분석 (STRATEGY-VAULT-DESIGN.md + SYSTEM_SPECIFICATION.md)

> 위 섹션 1~6은 코드 레벨 비교. 이 섹션은 **설계문서**에서 발견된 추가 갭.

### 🔴 Critical — 설계 수준에서 누락

#### 7.1 비상 정지 시스템 (Emergency Pause)
- **StrategyVault**: `toggle_pause` instruction → 관리자가 플랫폼 전체 즉시 정지
  - `is_paused = true` → 새 전략 등록/신호 기록 전부 차단
- **TradeCoach-AI**: 비상 정지 메커니즘 없음. 서버 장애나 보안 이슈 시 개별 프로세스 수동 중지 필요

#### 7.2 시간 조작 방지 (Timestamp Integrity)
- **StrategyVault**: 솔라나 블록 타임스탬프(`Clock::get().unix_timestamp`) 사용 → 사용자 조작 불가
  - 거래소 타임스탬프는 "참고용"으로만 기록, 신뢰 소스는 온체인 시간
- **TradeCoach-AI**: `timestamp=0` 전달 시 `int(time.time())` 사용 → 서버 시간 의존, 조작 가능

#### 7.3 Signal Sequence 무결성
- **StrategyVault**: 각 Signal에 `sequence: u64` (전략 내 순번) + `strategy.signal_count` 자동 증가
  - 순번 누락/중복 감지 가능
- **TradeCoach-AI**: `leaf_index`가 로컬 버퍼 기준이라 재시작 시 리셋됨 → 순번 연속성 보장 안 됨

#### 7.4 PnL Overflow 방지
- **StrategyVault**: `u128` 중간값 사용 후 `i64::MAX`로 cap
  - `(exit - entry) * quantity * leverage` 계산 시 overflow 방지
- **TradeCoach-AI**: Python이므로 overflow 위험은 낮지만, Solana 온체인 기록 시 정수 스케일링(1e8) 미사용

#### 7.5 Celery 비동기 백테스트 큐
- **BinanceTrader**: Celery + Redis로 백테스트를 백그라운드 task로 실행
  - `task_id` 반환 → 진행률 WebSocket 스트리밍 → 결과 조회
- **TradeCoach-AI**: 백테스트가 동기 실행 (API 응답 대기) → 대규모 데이터 시 타임아웃 위험

### 🟡 Important — 기능 수준에서 부족

#### 7.6 실매매 모드 (Live Trading)
- **BinanceTrader**: `LiveRunner` — PaperRunner와 동일 파이프라인 + `BinanceOrderAPI.place_market_order()` 실주문
  - User stream WebSocket으로 체결 확인
- **TradeCoach-AI**: 모의투자만 지원. 실거래 경로 없음

#### 7.7 Balance/Position 관리 시스템
- **BinanceTrader**: `BalanceManager` + `PositionManager` 분리
  - `deduct_margin()` → 잔고 부족 시 거부
  - `release_margin(margin, pnl)` → 증거금 반환 + PnL 정산
  - `update_prices()` → 미실현 PnL 실시간 갱신
- **TradeCoach-AI**: `DemoSession` dataclass에 뭉뚱그려 있음. 증거금 관리 없음

#### 7.8 Binance API Key 암호화 저장
- **BinanceTrader**: `binance_api_key_enc`, `binance_secret_key_enc` (AES 암호화 후 DB 저장)
- **TradeCoach-AI**: Binance API Key 저장 메커니즘 없음 (향후 실거래 지원 시 필요)

#### 7.9 대여(Rental) 에스크로 자동 정산
- **StrategyVault**: 에스크로 PDA에 SOL 예치 → `daily_settle` (누구나 crank 가능) → 일할 정산
  - `available_balance = deposited - settled - refunded`
  - 만료 시 `expire_rental` → 잔액 자동 환불
- **TradeCoach-AI**: 마켓플레이스 에스크로 메커니즘 없음

#### 7.10 Ranking 점수 계산 공식
- **StrategyVault**:
  ```
  score = (total_return_bps * 40%) + (win_rate_bps * 30%) - (max_drawdown_bps * 30%)
  Verified 전략: score *= 2 (보너스)
  ```
  - 카테고리별 Top 10, bubble sort 정렬
- **TradeCoach-AI**: 랭킹 시스템 없음

#### 7.11 WebSocket 진행률 스트리밍
- **BinanceTrader**:
  - `/ws/backtest/{task_id}` — 백테스트 진행률 실시간 전달
  - `/ws/ai/chat` — AI 채팅 양방향 WebSocket
  - `/ws/trading` — 주문 체결/잔고 변경 실시간
- **TradeCoach-AI**: 폴링 방식만 사용 (2초 간격). WebSocket 채널 없음 (차트용 제외)

#### 7.12 TradingView Webhook 지원
- **StrategyVault Gateway**: `POST /api/v1/webhook` — TradingView alert 형식 직접 수신
- **BinanceTrader**: Webhook + HMAC-SHA256 서명
- **TradeCoach-AI**: 외부 시그널 수신 엔드포인트 없음

### 🟢 Recommended — 품질/안정성 갭

#### 7.13 구조화된 로깅 (JSON Logging)
- **StrategyVault Gateway**: 모든 요청에 JSON 구조화 로그 (timestamp, method, path, status, duration_ms, ip)
  - `/metrics` 엔드포인트: signals_total, signals_failed, last_signal_at
- **TradeCoach-AI**: Python logging 기본 포맷. 구조화된 모니터링 없음

#### 7.14 Pyth Oracle 신뢰도/Staleness 검증
- **StrategyVault**: 5단계 검증:
  1. 계정 크기 ≥ 240 bytes
  2. Magic number = 0xa1b2c3d4
  3. publish_time > now - 30초 (staleness)
  4. confidence < price × 2% (신뢰도)
  5. price > 0 (유효 가격)
- **TradeCoach-AI**: Pyth 연동 자체가 없음

#### 7.15 Signal 불변성 (Immutability)
- **StrategyVault**: Signal에 update/delete instruction이 **아예 존재하지 않음** → 완전 불변
  - 전략 삭제해도 Signal PDA는 영구 보존
- **TradeCoach-AI**: `_signal_buffer`는 메모리 기반 → 서버 재시작 시 소실. `flush_signals_to_chain()`도 실제 온체인 TX 미구현 (Merkle root 계산만)

#### 7.16 멀티 심볼 전략 (최대 5개)
- **StrategyVault**: 하나의 전략이 최대 5개 심볼 동시 거래 (BTCUSDT + ETHUSDT + ...)
- **TradeCoach-AI**: 전략당 1개 `target_pair`만 지원

#### 7.17 Docker Compose 인프라
- **BinanceTrader**: PostgreSQL 16 + Redis 7 Docker Compose 파일 제공
- **TradeCoach-AI**: Supabase 의존 (로컬 개발환경 설정 파일 없음)

---

## 8. 전체 액션 아이템 (통합 — 코드 + 설계문서 분석)

| # | 우선순위 | 작업 | 출처 | 예상 범위 |
|---|---------|------|------|---------|
| 1 | 🔴 | 기술 지표 25개 추가 (ADX, SAR, CCI, MFI, OBV 등) | 코드 비교 | 중 |
| 2 | 🔴 | IS/OOS 과적합 검증 백테스트에 통합 | 코드 비교 | 중 |
| 3 | 🔴 | 슬리피지 시뮬레이션 (engine.py에 0.01% 추가) | 코드 비교 | 소 |
| 4 | 🔴 | WebSocket 가격 피드 (demo_price_feed 업그레이드) | 코드 비교 | 중 |
| 5 | 🔴 | 비상 정지 시스템 (admin toggle_pause 엔드포인트) | 설계문서 | 소 |
| 6 | 🔴 | Signal Sequence 무결성 (재시작 안전한 순번 관리) | 설계문서 | 소 |
| 7 | 🔴 | 비동기 백테스트 큐 (Celery 또는 asyncio.Task + 진행률) | 설계문서 | 중 |
| 8 | 🟡 | CAGR 메트릭 추가 | 코드 비교 | 소 |
| 9 | 🟡 | Pyth Oracle 이중 가격 검증 (5단계) | 설계문서 | 중 |
| 10 | 🟡 | Telegram/Discord 알림 채널 | 코드 비교 | 중 |
| 11 | 🟡 | 모의투자 세션 DB 저장 (Supabase) | 코드 비교 | 중 |
| 12 | 🟡 | Balance/Position Manager 분리 (증거금 관리) | 설계문서 | 중 |
| 13 | 🟡 | 실매매 모드 (Binance 실주문) | 설계문서 | 대 |
| 14 | 🟡 | WebSocket 진행률 스트리밍 (백테스트, 채팅) | 설계문서 | 중 |
| 15 | 🟡 | TradingView Webhook 수신 엔드포인트 | 설계문서 | 소 |
| 16 | 🟡 | Ranking 점수 계산 + 리더보드 | 설계문서 | 중 |
| 17 | 🟢 | 독립 검증 시스템 (100+ 신호 → Verified) | 코드 비교 | 대 |
| 18 | 🟢 | 마켓플레이스 에스크로 + 일일 정산 | 코드 비교 | 대 |
| 19 | 🟢 | 구조화된 로깅 + /metrics 엔드포인트 | 설계문서 | 소 |
| 20 | 🟢 | Signal 불변성 (실제 온체인 TX 구현) | 설계문서 | 대 |
| 21 | 🟢 | 멀티 심볼 전략 (최대 5개) | 설계문서 | 중 |
| 22 | 🟢 | Docker Compose 로컬 개발환경 | 설계문서 | 소 |
| 23 | 🟢 | Binance API Key 암호화 저장 | 설계문서 | 소 |

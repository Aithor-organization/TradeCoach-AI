# TradeCoach-AI 마켓플레이스 구현 계획서

> 작성일: 2026-03-25
> 상태: Phase 1-2 완료, Phase 3-5 다음 세션에서 진행

---

## 완료된 작업 (이번 세션)

### Phase 1: 온체인 인프라 ✅
- [x] 4개 Solana 프로그램 Devnet 배포
  - strategy_registry: `6EuhmRPHqN4r6SoP8anEpm2ZmVuQoHLLWre4zEPdc6Bo`
  - signal_recorder: `HydMVYPxrrCkFAnwaZLKeYzPoEvF1qSSDYnX1fSC2J89`
  - strategy_marketplace: `BKmM7ZHuKmg6f5FQbv6rTF44sJkYNR2UsSbvRFGgnmU1`
  - performance_verifier: `J3LeviD4zd9y5izVHLLwgopvEM82A9aUdgXi29wioNCL`
- [x] 서버 키페어 생성 + Devnet SOL 에어드랍

### Phase 2: 거래 기록 시스템 ✅
- [x] 모의투자 Stop → Merkle root 온체인 기록 (Memo TX)
- [x] Off-chain Merkle Tree + 개별 신호 proof 생성/검증
- [x] 프론트엔드 TX signature + Solana Explorer 링크
- [x] 비용: 0.000005 SOL/Stop (TX 수수료만)

### Phase 2.5: 전략 등록 + 성과 관리 API ✅
- [x] `POST /blockchain/strategy/register-onchain` — 전략 Memo TX 등록
- [x] `GET /blockchain/strategy/{id}/performance` — 누적 성과 조회
- [x] `GET /blockchain/strategy/{id}/trade-history` — 거래 히스토리
- [x] `POST /blockchain/merkle/verify` — 개별 거래 Merkle proof 검증
- [x] 모의투자 Stop 시 자동 성과 업데이트

---

## 남은 작업

### Phase 3: Anchor Instruction 직접 호출 (복잡도: HIGH)

현재 Memo TX로 "증명"만 남기고 있지만, StrategyVault 프로그램의 실제 instruction을 호출하면 온체인에 구조화된 데이터가 저장됩니다.

#### 3-1: initialize_platform (1회성)
```
파일: backend/services/blockchain/anchor_client.py (신규)
작업:
  - strategy-registry IDL (target/idl/strategy_registry.json) 파싱
  - initialize_platform instruction 구성 (Borsh 직렬화)
  - Platform PDA 주소 계산: seeds = [b"platform"]
  - TX 서명 및 전송
  - 1회만 실행하면 됨 (Platform 계정 이미 존재하면 스킵)

핵심 데이터:
  - fee_percentage: u16 (예: 500 = 5%)
  - min_purchase_price: u64
  - min_rental_price: u64

비용: ~0.003 SOL (Platform 계정 rent)
```

#### 3-2: register_strategy
```
파일: backend/services/blockchain/anchor_client.py
작업:
  - NFT 민팅 시 자동 호출
  - Strategy PDA 생성: seeds = [b"strategy", platform.key, strategy_count.to_le_bytes()]
  - 전략 메타데이터 온체인 저장 (이름, 설명, 심볼, 가격 등)

instruction args:
  - name: [u8; 64]
  - description: [u8; 256]
  - metadata_uri: [u8; 128] (Arweave URL)
  - market_type: u8 (0=spot, 1=futures)
  - time_frame: u8
  - symbols: [[u8; 16]; 5]
  - symbol_count: u8
  - backtest_start: i64
  - backtest_end: i64
  - backtest_return_pct: i16
  - purchase_price: u64
  - rental_price_per_day: u64

비용: ~0.005 SOL (Strategy 계정 659 bytes)
```

#### 3-3: Borsh 직렬화 구현
```
파일: backend/services/blockchain/borsh_utils.py (신규)
작업:
  - Python에서 Anchor Borsh 직렬화 수동 구현
  - 또는 anchorpy 설치 (pip install anchorpy)
  - IDL JSON → instruction data 변환
  - Discriminator 계산: SHA256("global:<instruction_name>")[:8]

참고: anchorpy 사용 시 IDL 파일만 있으면 자동으로 instruction 구성 가능
  from anchorpy import Program, Provider
  program = Program(idl, program_id, provider)
  await program.rpc["register_strategy"](args, ctx=ctx)
```

### Phase 4: 성과 검증 온체인화 (복잡도: MEDIUM)

#### 4-1: update_performance instruction
```
작업:
  - 모의투자 Stop 시 performance_verifier.update_performance() 호출
  - Performance PDA에 수익률, 승률, 최대 낙폭 등 기록
  - seeds = [b"performance", strategy.key]

instruction args:
  - period_return_bps: i32 (수익률 bps)
  - period_trades: u32
  - period_wins: u32

비용: ~0.003 SOL (Performance 계정 생성, 이후 업데이트는 TX 수수료만)
```

#### 4-2: verify_track_record instruction
```
작업:
  - 일정 기간 후 자동 검증 트리거
  - "이 전략이 N일간 X% 수익을 달성했음"을 온체인에서 검증
  - 검증 완료 시 verified = true 마킹

조건:
  - 최소 30일 + 100건 거래 (설정 가능)
  - is_verified: true → 마켓플레이스 등록 자격
```

### Phase 5: 마켓플레이스 프론트엔드 (복잡도: HIGH)

#### 5-1: 마켓플레이스 페이지 (/marketplace)
```
파일: frontend/app/marketplace/page.tsx (기존 파일 개선)
작업:
  - 온체인 검증된 전략 목록 표시
  - 각 전략의 성과 데이터 (수익률, 승률, 기간) 표시
  - 온체인 검증 배지 (verified ✓)
  - 가격 표시 (구매/대여)
  - 정렬/필터 (수익률순, 승률순, 최신순)
```

#### 5-2: 전략 상세 페이지
```
파일: frontend/app/marketplace/[id]/page.tsx (신규)
표시 내용:
  - 전략 설명 + 조건
  - 온체인 성과 차트 (누적 수익률 그래프)
  - 개별 거래 기록 + Merkle proof 검증 버튼
  - TX 히스토리 (모든 온체인 기록 링크)
  - 구매/대여 버튼
```

#### 5-3: 구매/대여 기능
```
작업:
  - Phantom 지갑 연결
  - strategy_marketplace.purchase() 또는 rent() instruction 호출
  - SOL 결제 → 에스크로 → 전략 접근 권한 부여
  - License PDA 생성으로 구매 증명

비용:
  - 구매: 판매자 설정 가격 + ~0.003 SOL (License 계정 rent)
  - 대여: 일일 가격 + ~0.003 SOL (Escrow 계정 rent)
```

---

## 구현 우선순위

```
Phase 3-1 (initialize_platform)   → 30분  | 선행 조건
Phase 3-2 (register_strategy)     → 1시간 | 전략 등록
Phase 3-3 (Borsh/anchorpy)        → 1시간 | 공통 유틸리티
Phase 4-1 (update_performance)    → 1시간 | 성과 기록
Phase 4-2 (verify_track_record)   → 30분  | 성과 검증
Phase 5-1 (마켓플레이스 페이지)    → 2시간 | UI
Phase 5-2 (전략 상세)             → 1시간 | UI
Phase 5-3 (구매/대여)             → 2시간 | Phantom + TX
```

**총 예상: 약 8-9시간 (2-3 세션)**

---

## 기술 스택

| 레이어 | 현재 | 목표 |
|--------|------|------|
| 거래 기록 | Memo TX + Merkle ✅ | 동일 유지 |
| 전략 등록 | Memo TX ✅ | Anchor register_strategy |
| 성과 관리 | 인메모리 ✅ | Anchor update_performance |
| 마켓플레이스 | 기존 DB 기반 | Anchor purchase/rent |
| 프론트엔드 | TX sig 표시 ✅ | 전체 마켓플레이스 UI |

---

## 파일 구조 (목표)

```
backend/services/blockchain/
├── __init__.py                    ← ✅ 완료
├── solana_client.py               ← ✅ 완료
├── onchain_client.py              ← ✅ 완료 (Memo TX)
├── signal_recorder.py             ← ✅ 완료 (Merkle + flush)
├── merkle_tree.py                 ← ✅ 완료 (Off-chain Merkle)
├── strategy_registry_client.py    ← ✅ 완료 (Memo 기반)
├── anchor_client.py               ← Phase 3 (Anchor instruction 직접 호출)
├── borsh_utils.py                 ← Phase 3 (Borsh 직렬화)
├── performance_verifier.py        ← ✅ 기존 (Phase 4에서 업그레이드)
├── strategy_nft.py                ← ✅ 기존
├── arweave_storage.py             ← ✅ 기존
└── pyth_client.py                 ← ✅ 기존
```

---

## Devnet Program IDs (참조)

```
strategy_registry    = 6EuhmRPHqN4r6SoP8anEpm2ZmVuQoHLLWre4zEPdc6Bo
signal_recorder      = HydMVYPxrrCkFAnwaZLKeYzPoEvF1qSSDYnX1fSC2J89
strategy_marketplace = BKmM7ZHuKmg6f5FQbv6rTF44sJkYNR2UsSbvRFGgnmU1
performance_verifier = J3LeviD4zd9y5izVHLLwgopvEM82A9aUdgXi29wioNCL

IDL 파일: TradeCoach-AI/target/idl/*.json
서버 키페어: ~/.config/solana/id.json
서버 공개키: CqSi1GaTXGPgGsAryuajmd449nL72EF1wGsen9idfDmg
```

---

## 다음 세션 시작 명령어

```bash
/auto 마켓플레이스 Phase 3 구현 — initialize_platform + register_strategy Anchor instruction 직접 호출
```

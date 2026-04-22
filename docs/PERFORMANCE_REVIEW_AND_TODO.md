# TradeCoach-AI Performance Review and TODO

## 목적
이 문서는 TradeCoach-AI 프로젝트를 검토하며 확인한 병목 지점, API 호출 제한, Supabase 연동 지연 가능성, 그리고 우선순위별 개선 작업을 정리한 문서입니다.

---

## 요약 결론
현재 구조에서 프론트엔드가 Supabase를 직접 느리게 조회하는 형태는 아닙니다.
대부분의 데이터 흐름은 아래와 같습니다.

- 브라우저
- FastAPI 백엔드
- Supabase REST

즉, 체감 지연은 보통 다음 원인에서 발생할 가능성이 큽니다.

1. 백엔드가 Supabase에서 너무 큰 payload를 가져옴 (`select=*` 사용 다수)
2. 프론트엔드 페이지가 핵심 데이터와 부가 데이터를 순차로 기다림
3. 백엔드가 매 요청마다 `httpx.AsyncClient()`를 새로 생성하여 연결 재사용 이점이 적음

---

## 아키텍처 관찰 사항

### 현재 데이터 접근 구조
- 프론트엔드는 주로 `NEXT_PUBLIC_API_URL` 기반으로 백엔드 API를 호출함
- Supabase 접근은 백엔드 `services/supabase_client.py`에서 수행됨
- 따라서 "Supabase 데이터가 프론트에서 늦게 뜬다"는 현상은
  - 프론트 직접 호출 문제라기보다
  - 백엔드의 Supabase 조회 방식과
  - 프론트의 로딩 대기 방식 때문에 발생할 가능성이 높음

### 관련 파일
- `frontend/lib/api.ts`
- `frontend/lib/blockchainApi.ts`
- `backend/services/supabase_client.py`

---

## Rate Limit / API 호출 제한 현황

### 공통 정책
- 인증 사용자는 `user_id` 기반 제한
- 미인증 사용자는 IP 기반 제한

### 관련 파일
- `backend/main.py`

### 엔드포인트별 제한

#### 인증
- `/auth/wallet`: `10/minute`
- `/auth/verify`: `5/minute`
- `/auth/register`: `5/minute`

#### 채팅
- `/chat/message`: `30/minute`
- `/chat/message/image`: `30/minute`
- `/chat/message/stream`: `30/minute`

#### 백테스트
- `/backtest/run`: `10/minute`
- `/backtest/isoos`: `5/minute`

#### 모의투자
- `/trading/demo/start`: `5/minute`

#### 최적화
- `/optimize/grid`: `5/minute`
- `/optimize/walk-forward`: `5/minute`

### 리뷰 의견
- 제한값 자체는 비정상적으로 보이지 않음
- 다만 폴링 기반 화면이 늘어나면 서버 read load가 증가할 수 있음
- 특히 optimization job polling, demo status polling은 동시 사용자 수 증가 시 부하 요인이 될 수 있음

---

## 주요 병목 분석

## 1. Supabase 조회에서 `select=*` 사용 다수
### 문제
여러 API가 필요한 컬럼만 고르지 않고 전체 컬럼을 조회함

### 영향
아래와 같은 큰 JSON 필드까지 함께 전달될 수 있음
- `parsed_strategy`
- `metrics`
- `equity_curve`
- `trade_log`
- `ai_summary`

### 특히 영향이 큰 위치
- 전략 목록 조회
- 전략 상세 조회
- 채팅 히스토리 조회
- 백테스트 히스토리 조회
- TX 기록 조회

### 관련 파일
- `backend/services/supabase_client.py`

### 우선 개선 방향
- 목록 API는 summary 전용 컬럼만 반환
- 상세 API만 큰 JSON 필드 반환
- 백테스트 히스토리 목록은 경량 필드만 내려주고, 상세 클릭 시 별도 조회

---

## 2. 백엔드에서 매 요청마다 `httpx.AsyncClient()` 새 생성
### 문제
Supabase 호출 함수 대부분이 요청마다 새 AsyncClient를 열고 닫음

### 영향
- 연결 재사용이 약함
- keep-alive 효율이 낮음
- 요청량이 늘수록 latency 누적 가능

### 관련 파일
- `backend/services/supabase_client.py`

### 우선 개선 방향
- 앱 수명주기 동안 재사용 가능한 shared AsyncClient 도입
- Supabase/외부 API 요청에 connection pooling 적용

---

## 3. 전략 상세 페이지 로딩이 순차적
### 문제
전략 상세 페이지에서
1. 전략 본문을 불러오고
2. 그 다음 백테스트 히스토리를 불러오며
3. 둘 다 끝나야 로딩 해제됨

### 영향
- 전략 자체는 빨리 표시할 수 있어도
- 히스토리 로딩 때문에 전체 페이지가 늦게 뜨는 체감 발생

### 관련 파일
- `frontend/app/strategies/[id]/page.tsx`
- `backend/routers/backtest.py`
- `backend/services/supabase_client.py`

### 우선 개선 방향
- 전략 본문 먼저 렌더
- 히스토리는 별도 skeleton / 비동기 로딩
- 페이지 핵심과 부가 정보를 분리

---

## 4. 백테스트 히스토리 payload가 무거울 가능성
### 문제
백테스트 결과 저장 시 `trade_log`, `ai_summary`가 metrics 안에 포함되어 저장됨
그리고 history 조회는 `select=*`라서 목록 용도인데도 큰 데이터가 같이 올 수 있음

### 관련 파일
- `backend/services/supabase_client.py`
- `backend/routers/backtest.py`

### 우선 개선 방향
- history list API: 경량 메타데이터만 반환
- backtest detail API: 선택 시 상세 데이터 반환

---

## 5. publish to marketplace 요청이 동기적으로 무거움
### 현재 수행 작업
한 번의 publish 요청에서 아래를 모두 수행함
- 전략 조회
- `trade_sessions` 최대 50개 조회
- 성과 계산
- Gemini 요약 생성
- DB 업데이트
- 블록체인 등록 시도

### 영향
- 버튼 클릭 후 응답이 길어질 수 있음
- 실패 원인 파악도 어려워질 수 있음

### 관련 파일
- `backend/routers/strategy.py`
- `backend/services/gemini.py`

### 우선 개선 방향
- publish는 job 기반 비동기 처리로 전환
- UI는 pending 상태 + 결과 polling 또는 SSE 사용

---

## 6. polling 기반 부하 지점

### optimization job polling
- 2초 간격, 최대 150회
- walk-forward는 3초 간격, 최대 200회

### demo trading status polling
- 2초 간격

### 관련 파일
- `frontend/lib/api.ts`
- `frontend/app/trading/page.tsx`

### 우선 개선 방향
- adaptive polling 도입
- 장기적으로 SSE/WebSocket 검토

---

## 7. 채팅 히스토리 전체 조회
### 문제
전략 채팅 패널이 마운트 시 전체 히스토리를 가져옴

### 영향
메시지가 많아질수록 초기 진입 속도 저하 가능

### 관련 파일
- `frontend/components/chat/StrategyChatPanel.tsx`
- `backend/services/supabase_client.py`

### 우선 개선 방향
- 최근 N개만 우선 조회
- 이전 메시지는 pagination / infinite scroll

---

## 상대적으로 잘 되어 있는 부분

### 1. 공개 전략 목록 캐시 헤더 존재
- `Cache-Control: public, max-age=60, stale-while-revalidate=30`
- 관련 파일: `backend/routers/strategy.py`

### 2. 마켓플레이스 목록의 N+1 방지
- 공개 전략 목록 후 온체인 정보는 IN 쿼리 1회 배치 조회
- 관련 파일: `backend/routers/strategy.py`

### 3. 성과 조회 배치 API 존재
- 마켓플레이스 목록에서 여러 전략 성과를 한 번에 조회 가능
- 관련 파일:
  - `backend/routers/blockchain.py`
  - `backend/services/supabase_client.py`
  - `frontend/lib/blockchainApi.ts`

### 4. 토큰 가격 조회는 비교적 안정적
- 프론트 30초 polling
- 백엔드 15초 캐시
- 큰 병목으로 보이지 않음
- 관련 파일:
  - `frontend/components/market/TokenPrices.tsx`
  - `backend/services/jupiter.py`

---

## 기능/응답 불일치 이슈

### 마켓플레이스 상세 API와 프론트 사용 방식 불일치
백엔드 공개 전략 상세 API는 `parsed_strategy`를 제거하고 `summary`만 남기는데,
프론트는 여전히 `parsed_strategy`를 읽는 코드가 존재함

### 영향
- 상세 페이지 일부 정보가 비어 보일 수 있음
- 성능 문제는 아니지만 API 계약 불일치 문제

### 관련 파일
- `backend/routers/strategy.py`
- `frontend/app/marketplace/[id]/page.tsx`

---

# 우선순위별 TODO

## P1 — 가장 먼저 할 일

### TODO 1. 백테스트 히스토리 API 경량화
- [ ] `/backtest/history/{strategy_id}` 응답에서 목록용 최소 필드만 반환
- [ ] `trade_log`, `equity_curve`, `ai_summary`는 상세 조회 시만 반환
- [ ] 필요 시 `/backtest/result/{id}`를 상세 전용으로 일원화

### TODO 2. 전략 상세 페이지 로딩 분리
- [ ] `getStrategy()` 완료 시 바로 본문 렌더
- [ ] `getBacktestHistory()`는 별도 비동기 로딩
- [ ] 히스토리 영역 skeleton 적용
- [ ] 전략 본문과 히스토리의 실패 처리를 분리

### TODO 3. Supabase select 최소화
- [ ] `get_strategies()`에서 `select=*` 제거
- [ ] `get_strategy_by_id()`도 사용 목적에 따라 경량/상세 분리 검토
- [ ] `get_backtests_by_strategy_id()`는 목록용 select로 변경
- [ ] `get_chat_messages()`는 최근 N개 제한 검토

### TODO 4. shared AsyncClient 도입
- [ ] Supabase용 공용 `httpx.AsyncClient` 생성
- [ ] lifespan에서 초기화/종료 처리
- [ ] `services/supabase_client.py` 전체에 적용

---

## P2 — 다음 단계 개선

### TODO 5. publish to marketplace 비동기 job화
- [ ] publish 요청 시 즉시 job_id 반환
- [ ] trade session 분석, AI summary, on-chain 등록은 백그라운드 실행
- [ ] 프론트에 진행 상태 표시

### TODO 6. polling 최적화
- [ ] optimization polling 간격/횟수 재검토
- [ ] demo trading status polling에 adaptive polling 도입
- [ ] 장기적으로 SSE/WebSocket 전환 검토

### TODO 7. 채팅 히스토리 pagination
- [ ] 최신 50개 우선 조회
- [ ] 이전 히스토리 추가 로드 버튼 또는 무한 스크롤 적용

---

## P3 — 정합성 및 품질 개선

### TODO 8. 마켓플레이스 상세 API 계약 정리
- [ ] 백엔드가 `summary`만 줄 경우 프론트도 `summary`를 사용하도록 정리
- [ ] 또는 공개 API에서 필요한 최소 `parsed_strategy` 필드만 유지

### TODO 9. 로그/관측성 강화
- [ ] 주요 API 응답시간 로깅
- [ ] Supabase 요청 시간 측정
- [ ] 큰 payload 응답 감지 로그 추가

### TODO 10. API별 payload 크기 점검 문서화
- [ ] 전략 목록
- [ ] 전략 상세
- [ ] 백테스트 히스토리
- [ ] 채팅 히스토리
- [ ] 마켓플레이스 상세

---

# 추천 실행 순서

## 1차 작업 묶음
1. 백테스트 히스토리 API 경량화
2. 전략 상세 페이지 로딩 분리
3. Supabase select 최소화

예상 효과:
- 전략 상세 페이지 체감 속도 개선
- 불필요한 payload 감소
- Supabase 응답시간/전송량 감소

## 2차 작업 묶음
1. shared AsyncClient 도입
2. 채팅 히스토리 제한
3. polling 최적화

예상 효과:
- 서버 요청 처리 안정성 개선
- 동시 사용자 증가 시 성능 저하 완화

## 3차 작업 묶음
1. publish 비동기 job화
2. 마켓플레이스 API 계약 정리
3. 관측성 추가

예상 효과:
- 무거운 작업의 UX 개선
- 장애/지연 원인 추적 용이

---

# 가장 먼저 확인할 실제 병목 후보

## 1순위
- 전략 상세 페이지 백테스트 히스토리 로딩
- 관련 파일:
  - `frontend/app/strategies/[id]/page.tsx`
  - `backend/services/supabase_client.py`

## 2순위
- Supabase 조회 전체 컬럼 반환
- 관련 파일:
  - `backend/services/supabase_client.py`

## 3순위
- publish 동기 처리
- 관련 파일:
  - `backend/routers/strategy.py`
  - `backend/services/gemini.py`

---

# 문서 메모
이 문서는 코드 수정 전 성능 리뷰 및 개선 계획 정리용입니다.
실제 수정 시에는 각 TODO를 작은 단위로 나누어 검증 가능한 변경으로 진행하는 것을 권장합니다.

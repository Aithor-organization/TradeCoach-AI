-- Phase 2-3: 최적화 결과 + 모의투자 테이블
-- 실행: Supabase SQL Editor에서 실행

-- 최적화 결과
CREATE TABLE IF NOT EXISTS optimization_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  method TEXT NOT NULL DEFAULT 'grid',
  params JSONB,
  metrics JSONB,
  rank INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 모의투자 세션
CREATE TABLE IF NOT EXISTS demo_sessions (
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
CREATE TABLE IF NOT EXISTS demo_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES demo_sessions(id),
  side TEXT NOT NULL,
  entry_price DECIMAL NOT NULL,
  exit_price DECIMAL,
  quantity DECIMAL,
  leverage INTEGER,
  pnl DECIMAL,
  exit_reason TEXT,
  entry_at TIMESTAMPTZ,
  exit_at TIMESTAMPTZ
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_opt_results_strategy ON optimization_results(strategy_id);
CREATE INDEX IF NOT EXISTS idx_demo_sessions_user ON demo_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_demo_trades_session ON demo_trades(session_id);

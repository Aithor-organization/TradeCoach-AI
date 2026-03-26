-- 트레이딩 세션 결과 + 개별 거래 기록 (성과 영속화)
-- Supabase SQL Editor에서 실행

-- 세션 결과 (전략별 누적 성과)
CREATE TABLE IF NOT EXISTS trade_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id VARCHAR(100) NOT NULL,
  session_id VARCHAR(100) NOT NULL,
  record_mode VARCHAR(10) DEFAULT 'test',
  symbol VARCHAR(20),
  leverage INTEGER DEFAULT 1,
  initial_balance DECIMAL DEFAULT 1000,
  final_balance DECIMAL,
  total_trades INTEGER DEFAULT 0,
  winning_trades INTEGER DEFAULT 0,
  total_pnl DECIMAL DEFAULT 0,
  win_rate DECIMAL DEFAULT 0,
  tx_signature VARCHAR(100),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 개별 거래 기록
CREATE TABLE IF NOT EXISTS trade_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id VARCHAR(100) NOT NULL,
  session_id VARCHAR(100) NOT NULL,
  trade_index INTEGER DEFAULT 0,
  side VARCHAR(10),
  entry_price DECIMAL,
  exit_price DECIMAL,
  pnl DECIMAL DEFAULT 0,
  exit_reason VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trade_sessions_strategy ON trade_sessions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trade_records_strategy ON trade_records(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trade_records_session ON trade_records(session_id);

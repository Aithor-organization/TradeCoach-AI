-- 트레이딩 TX 기록 테이블 (하이브리드: DB 캐시 + 온체인 검증)
-- Supabase SQL Editor에서 실행

CREATE TABLE IF NOT EXISTS trade_tx_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id VARCHAR(100) NOT NULL,
  session_id VARCHAR(100),
  tx_signature VARCHAR(100) NOT NULL UNIQUE,
  merkle_root VARCHAR(64),
  trade_hash VARCHAR(64),
  trades_count INTEGER DEFAULT 0,
  network VARCHAR(20) DEFAULT 'devnet',
  explorer_url TEXT,
  record_mode VARCHAR(10) DEFAULT 'verify',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trade_tx_strategy ON trade_tx_records(strategy_id);
CREATE INDEX IF NOT EXISTS idx_trade_tx_created ON trade_tx_records(created_at DESC);

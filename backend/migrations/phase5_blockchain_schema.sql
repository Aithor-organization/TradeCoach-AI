-- Phase 5: 블록체인 통합 테이블
-- 실행: Supabase SQL Editor에서 실행

-- 온체인 전략 (cNFT)
CREATE TABLE IF NOT EXISTS onchain_strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  asset_id VARCHAR(44) NOT NULL,
  merkle_tree VARCHAR(44) NOT NULL,
  strategy_hash VARCHAR(64) NOT NULL,
  arweave_uri TEXT,
  is_public BOOLEAN DEFAULT FALSE,
  registered_at TIMESTAMPTZ DEFAULT NOW()
);

-- 온체인 매매 신호 (로컬 캐시)
CREATE TABLE IF NOT EXISTS onchain_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id),
  leaf_index INTEGER NOT NULL,
  signal_hash VARCHAR(64) NOT NULL,
  signal_type TEXT NOT NULL,
  symbol VARCHAR(20),
  price DECIMAL,
  leverage INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_onchain_strategies_sid ON onchain_strategies(strategy_id);
CREATE INDEX IF NOT EXISTS idx_onchain_signals_sid ON onchain_signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_onchain_signals_type ON onchain_signals(signal_type);

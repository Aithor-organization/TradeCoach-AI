-- TradeCoach AI DB 스키마
-- Supabase SQL Editor에서 실행

-- 사용자 (지갑 기반 인증)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wallet_address VARCHAR(44) UNIQUE NOT NULL,
  display_name VARCHAR(50),
  tier VARCHAR(10) DEFAULT 'free',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Nonce 저장 (지갑 인증용)
CREATE TABLE IF NOT EXISTS nonces (
  wallet_address VARCHAR(44) PRIMARY KEY,
  nonce TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 전략
CREATE TABLE IF NOT EXISTS strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  raw_input TEXT NOT NULL,
  input_type VARCHAR(10) DEFAULT 'text',
  image_url TEXT,
  parsed_strategy JSONB NOT NULL,
  status VARCHAR(20) DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 백테스트 결과
CREATE TABLE IF NOT EXISTS backtest_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  total_return DECIMAL(10,2),
  max_drawdown DECIMAL(10,2),
  sharpe_ratio DECIMAL(5,2),
  win_rate DECIMAL(5,2),
  total_trades INTEGER,
  token_pair VARCHAR(20),
  timeframe VARCHAR(10),
  start_date DATE,
  end_date DATE,
  equity_curve JSONB,
  trade_log JSONB,
  parsed_strategy JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 채팅 히스토리
CREATE TABLE IF NOT EXISTS chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  role VARCHAR(10) NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON strategies(user_id);
CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_backtest_strategy_id ON backtest_results(strategy_id);
CREATE INDEX IF NOT EXISTS idx_chat_strategy_id ON chat_messages(strategy_id);
CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_messages(created_at);

-- RLS (Row Level Security) - 서비스 키 바이패스 활성화
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE nonces ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- 서비스 키(backend)에서 모든 작업 허용
CREATE POLICY IF NOT EXISTS "service_role_users" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "service_role_nonces" ON nonces FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "service_role_strategies" ON strategies FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "service_role_backtest" ON backtest_results FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "service_role_chat" ON chat_messages FOR ALL USING (true) WITH CHECK (true);

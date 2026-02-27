-- Migration 001: nonces 테이블 추가 + backtest_results에 parsed_strategy 컬럼 추가
-- 기존 DB에 적용할 ALTER문
-- 실행: Supabase SQL Editor에서 실행

-- 1. nonces 테이블 생성
CREATE TABLE IF NOT EXISTS nonces (
  wallet_address VARCHAR(44) PRIMARY KEY,
  nonce TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. backtest_results에 parsed_strategy 컬럼 추가 (이미 있으면 무시)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'backtest_results' AND column_name = 'parsed_strategy'
  ) THEN
    ALTER TABLE backtest_results ADD COLUMN parsed_strategy JSONB;
  END IF;
END $$;

-- 3. RLS 활성화
ALTER TABLE nonces ENABLE ROW LEVEL SECURITY;

-- 4. 서비스 키 정책 (이미 존재하면 무시)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'nonces' AND policyname = 'service_role_nonces'
  ) THEN
    CREATE POLICY service_role_nonces ON nonces FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- 5. 오래된 nonce 자동 삭제 (10분 이상)
-- cron job이나 수동 실행:
-- DELETE FROM nonces WHERE created_at < NOW() - INTERVAL '10 minutes';

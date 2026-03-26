-- strategies 테이블에 is_public 컬럼 추가
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_strategies_public ON strategies(is_public) WHERE is_public = TRUE;

-- Marketplace 필드 추가: AI 요약 + 성과 지표
ALTER TABLE strategies
  ADD COLUMN IF NOT EXISTS marketplace_summary text,
  ADD COLUMN IF NOT EXISTS marketplace_metrics jsonb;

-- 인덱스: 공개 전략 조회 최적화
CREATE INDEX IF NOT EXISTS idx_strategies_is_public
  ON strategies(is_public) WHERE is_public = true;

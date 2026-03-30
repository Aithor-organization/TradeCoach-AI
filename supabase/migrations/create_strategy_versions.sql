-- Strategy Version Snapshots: 민팅 시점의 전략을 불변으로 보존
CREATE TABLE IF NOT EXISTS strategy_versions (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  strategy_id uuid NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
  version int NOT NULL DEFAULT 1,
  parsed_strategy jsonb NOT NULL,
  mint_tx text,
  mint_hash text,
  mint_network text DEFAULT 'devnet',
  label text,
  created_at timestamptz DEFAULT now(),

  -- 같은 전략에 같은 버전 번호 중복 방지
  UNIQUE(strategy_id, version)
);

-- 인덱스: 전략별 버전 조회 최적화
CREATE INDEX IF NOT EXISTS idx_strategy_versions_strategy_id
  ON strategy_versions(strategy_id, version DESC);

-- RLS 정책 (선택적: 소유자만 조회)
ALTER TABLE strategy_versions ENABLE ROW LEVEL SECURITY;

-- 모든 인증된 사용자가 자신의 전략 버전을 조회 가능
CREATE POLICY "Users can view own strategy versions" ON strategy_versions
  FOR SELECT USING (
    strategy_id IN (
      SELECT id FROM strategies WHERE user_id = auth.uid()
    )
  );

-- 서비스 역할(백엔드)은 모든 작업 가능
CREATE POLICY "Service role full access" ON strategy_versions
  FOR ALL USING (true) WITH CHECK (true);

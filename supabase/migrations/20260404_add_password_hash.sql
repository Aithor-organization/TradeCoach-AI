-- 사용자 비밀번호 해시 컬럼 추가
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;

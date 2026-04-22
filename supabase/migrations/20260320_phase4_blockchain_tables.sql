CREATE TABLE IF NOT EXISTS signal_sequence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id TEXT NOT NULL UNIQUE,
    current_seq BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS blockchain_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('BUY','SELL')),
    entry_price NUMERIC(20,8) NOT NULL,
    exit_price NUMERIC(20,8),
    pyth_price NUMERIC(20,8),
    tx_hash TEXT,
    sequence_number BIGINT NOT NULL,
    is_closed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bc_signals_strategy ON blockchain_signals(strategy_id, created_at DESC);
CREATE TABLE IF NOT EXISTS strategy_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id TEXT NOT NULL,
    verifier_id TEXT NOT NULL,
    is_valid BOOLEAN NOT NULL,
    metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(strategy_id, verifier_id)
);

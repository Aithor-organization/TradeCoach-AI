use anchor_lang::prelude::*;

#[account]
pub struct Performance {
    /// Strategy PDA key
    pub strategy: Pubkey,

    // Trade counts
    pub total_signals: u64,
    pub total_trades: u64,
    pub winning_trades: u64,
    pub win_rate_bps: u16,

    // PnL metrics
    pub total_pnl_scaled: i64,      // 1e8 scaled
    pub total_return_bps: i32,
    pub max_drawdown_bps: u16,
    pub sharpe_ratio_scaled: i16,   // x100
    pub profit_factor_scaled: u16,  // x100

    // Statistics
    pub avg_holding_seconds: u64,
    pub best_trade_pnl: i64,
    pub worst_trade_pnl: i64,
    pub max_consecutive_wins: u16,
    pub max_consecutive_losses: u16,

    // Mode breakdown
    pub paper_signals: u64,
    pub live_signals: u64,
    pub paper_pnl_scaled: i64,
    pub live_pnl_scaled: i64,

    // Verification
    pub last_signal_at: i64,
    pub last_verified_at: i64,
    pub verification_count: u32,
    pub is_verified: bool,

    // Tracking
    pub first_signal_at: i64,
    pub current_streak: i16,        // positive = wins, negative = losses
    pub peak_equity_scaled: i64,    // for drawdown calculation

    pub bump: u8,
}

impl Performance {
    pub const SEED: &'static [u8] = b"perf";

    pub const SIZE: usize = 8   // discriminator
        + 32                    // strategy
        + 8 + 8 + 8 + 2       // trade counts
        + 8 + 4 + 2 + 2 + 2   // pnl metrics
        + 8 + 8 + 8 + 2 + 2   // statistics
        + 8 + 8 + 8 + 8       // mode breakdown
        + 8 + 8 + 4 + 1       // verification
        + 8 + 2 + 8           // tracking
        + 1;                   // bump

    /// Minimum signals required for verification
    pub const MIN_SIGNALS: u64 = 100;
    /// Minimum track record in seconds (90 days)
    pub const MIN_TRACK_RECORD_SECONDS: i64 = 90 * 86_400;
    /// Minimum independent verifications
    pub const MIN_VERIFICATIONS: u32 = 3;
}

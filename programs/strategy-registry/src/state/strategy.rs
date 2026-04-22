use anchor_lang::prelude::*;

#[account]
pub struct Strategy {
    /// Unique strategy ID
    pub id: u64,
    /// Strategy owner
    pub authority: Pubkey,

    // Basic info (on-chain)
    /// Strategy name (UTF-8, 64 bytes max)
    pub name: [u8; 64],
    /// Short description (UTF-8, 256 bytes max)
    pub description: [u8; 256],
    /// Arweave URI for detailed data + charts
    pub metadata_uri: [u8; 128],

    // Strategy attributes
    /// Trading market
    pub market: Market,
    /// Candle timeframe
    pub time_frame: TimeFrame,
    /// Trading symbols (up to 5, e.g. "BTCUSDT")
    pub symbols: [[u8; 16]; 5],
    /// Number of active symbols
    pub symbol_count: u8,

    // Backtest summary (key metrics on-chain)
    pub backtest: BacktestSummary,

    // State
    /// Whether the strategy is active
    pub is_active: bool,
    /// Whether performance criteria are met
    pub is_verified: bool,
    /// Registration timestamp
    pub created_at: i64,

    // Pricing
    /// Permanent purchase price in lamports
    pub price_lamports: u64,
    /// Daily rental price in lamports
    pub rent_lamports_per_day: u64,

    /// Total signals recorded (for integrity check)
    pub signal_count: u64,

    /// PDA bump
    pub bump: u8,
}

impl Strategy {
    pub const SEED: &'static [u8] = b"strategy";

    pub const SIZE: usize = 8   // discriminator
        + 8                     // id
        + 32                    // authority
        + 64                    // name
        + 256                   // description
        + 128                   // metadata_uri
        + 1                     // market
        + 1                     // time_frame
        + (16 * 5)              // symbols
        + 1                     // symbol_count
        + BacktestSummary::SIZE // backtest
        + 1                     // is_active
        + 1                     // is_verified
        + 8                     // created_at
        + 8                     // price_lamports
        + 8                     // rent_lamports_per_day
        + 8                     // signal_count
        + 1;                    // bump
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default)]
pub struct BacktestSummary {
    /// Backtest period start (unix timestamp)
    pub period_start: i64,
    /// Backtest period end (unix timestamp)
    pub period_end: i64,
    /// Total number of trades
    pub total_trades: u32,
    /// Win rate in basis points (5000 = 50%)
    pub win_rate_bps: u16,
    /// Total return in basis points (can be negative)
    pub total_return_bps: i32,
    /// Maximum drawdown in basis points
    pub max_drawdown_bps: u16,
    /// Sharpe ratio scaled by 100 (185 = 1.85)
    pub sharpe_ratio_scaled: i16,
    /// Profit factor scaled by 100 (210 = 2.10)
    pub profit_factor_scaled: u16,
    /// Average leverage used
    pub avg_leverage: u8,
    /// Maximum leverage used
    pub max_leverage: u8,
}

impl BacktestSummary {
    pub const SIZE: usize = 8 + 8 + 4 + 2 + 4 + 2 + 2 + 2 + 1 + 1; // 34
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum Market {
    BinanceFutures,
    BinanceSpot,
    BybitFutures,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum TimeFrame {
    M1,
    M5,
    M15,
    H1,
    H4,
    D1,
    W1,
}

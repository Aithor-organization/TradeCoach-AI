use anchor_lang::prelude::*;
use super::signal::{Side, TradingMode};

#[account]
pub struct Position {
    /// Strategy PDA
    pub strategy: Pubkey,
    /// Trading symbol
    pub symbol: [u8; 16],
    /// Long or Short
    pub side: Side,
    /// Leverage
    pub leverage: u8,
    /// Entry price (scaled by 1e8)
    pub entry_price: u64,
    /// Entry signal sequence number
    pub entry_signal_seq: u64,
    /// Quantity (scaled by 1e8)
    pub quantity_scaled: u64,
    /// When the position was opened
    pub opened_at: i64,
    /// Whether position is still open
    pub is_open: bool,
    /// Paper or Live
    pub mode: TradingMode,
    /// PDA bump
    pub bump: u8,
}

impl Position {
    pub const SEED: &'static [u8] = b"position";

    pub const SIZE: usize = 8   // discriminator
        + 32                    // strategy
        + 16                    // symbol
        + 1                     // side
        + 1                     // leverage
        + 8                     // entry_price
        + 8                     // entry_signal_seq
        + 8                     // quantity_scaled
        + 8                     // opened_at
        + 1                     // is_open
        + 1                     // mode
        + 1;                    // bump
}

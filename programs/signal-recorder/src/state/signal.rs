use anchor_lang::prelude::*;

#[account]
pub struct Signal {
    /// Strategy PDA this signal belongs to
    pub strategy: Pubkey,
    /// Sequence number within the strategy (0-indexed)
    pub sequence: u64,

    // Signal info
    /// Type of signal
    pub signal_type: SignalType,
    /// Paper trading or live trading
    pub mode: TradingMode,
    /// Trading symbol e.g. "BTCUSDT" (16 bytes)
    pub symbol: [u8; 16],
    /// Long or Short
    pub side: Side,
    /// Leverage multiplier (1-125)
    pub leverage: u8,
    /// Quantity in base asset (scaled by 1e8)
    pub quantity_scaled: u64,

    // Dual price recording
    /// Exchange execution price (scaled by 1e8)
    pub exchange_price: u64,
    /// Pyth oracle verified price (scaled by 1e8)
    pub pyth_price: u64,
    /// Price delta between exchange and Pyth (basis points)
    pub price_delta_bps: u16,
    /// Pyth confidence interval (scaled by 1e8)
    pub pyth_confidence: u64,
    /// Pyth price publish time
    pub pyth_publish_time: i64,

    // Timestamps
    /// Exchange execution timestamp (provided off-chain, reference only)
    pub exchange_timestamp: i64,
    /// Solana slot number (trustworthy)
    pub slot: u64,
    /// Solana block timestamp (trustworthy)
    pub timestamp: i64,

    /// PDA bump
    pub bump: u8,
}

impl Signal {
    pub const SEED: &'static [u8] = b"signal";

    pub const SIZE: usize = 8   // discriminator
        + 32                    // strategy
        + 8                     // sequence
        + 1                     // signal_type
        + 1                     // mode
        + 16                    // symbol
        + 1                     // side
        + 1                     // leverage
        + 8                     // quantity_scaled
        + 8                     // exchange_price
        + 8                     // pyth_price
        + 2                     // price_delta_bps
        + 8                     // pyth_confidence
        + 8                     // pyth_publish_time
        + 8                     // exchange_timestamp
        + 8                     // slot
        + 8                     // timestamp
        + 1;                    // bump
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum SignalType {
    Buy,
    Sell,
    CloseLong,
    CloseShort,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum TradingMode {
    Paper,
    Live,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum Side {
    Long,
    Short,
}

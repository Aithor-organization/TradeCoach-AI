use anchor_lang::prelude::*;

#[error_code]
pub enum SignalError {
    #[msg("Only the strategy owner can record signals")]
    UnauthorizedSignalAction,

    #[msg("Strategy is not active")]
    StrategyInactive,

    #[msg("Invalid Pyth price account")]
    InvalidPythAccount,

    #[msg("Pyth price is stale (> 30 seconds old)")]
    PythPriceStale,

    #[msg("Pyth confidence interval too wide (> 2% of price)")]
    PythConfidenceTooWide,

    #[msg("Invalid Pyth price (zero or negative)")]
    InvalidPythPrice,

    #[msg("Invalid leverage: must be 1-125")]
    InvalidLeverage,

    #[msg("Invalid quantity: must be > 0")]
    InvalidQuantity,

    #[msg("Exchange price must be > 0")]
    InvalidExchangePrice,

    #[msg("Position is not open")]
    PositionNotOpen,

    #[msg("Position is already open for this symbol")]
    PositionAlreadyOpen,

    #[msg("Signal type does not match position side")]
    SignalSideMismatch,

    #[msg("Arithmetic overflow")]
    ArithmeticOverflow,

    #[msg("Batch size exceeds maximum of 5")]
    BatchTooLarge,
}

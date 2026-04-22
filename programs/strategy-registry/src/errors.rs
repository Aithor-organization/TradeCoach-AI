use anchor_lang::prelude::*;

#[error_code]
pub enum StrategyError {
    #[msg("Only the platform authority can perform this action")]
    UnauthorizedPlatformAction,

    #[msg("Only the strategy owner can perform this action")]
    UnauthorizedStrategyAction,

    #[msg("Strategy name cannot be empty")]
    EmptyName,

    #[msg("Strategy is not active")]
    StrategyInactive,

    #[msg("Cannot delete strategy with active rentals")]
    ActiveRentalsExist,

    #[msg("Cannot delete strategy with open positions")]
    OpenPositionsExist,

    #[msg("Invalid fee: must be <= 10000 basis points (100%)")]
    InvalidFee,

    #[msg("Invalid backtest period: end must be after start")]
    InvalidBacktestPeriod,

    #[msg("Symbol count exceeds maximum of 5")]
    TooManySymbols,

    #[msg("Price must be greater than zero")]
    InvalidPrice,

    #[msg("Arithmetic overflow")]
    ArithmeticOverflow,

    #[msg("Platform is paused — all operations are temporarily blocked")]
    PlatformPaused,
}

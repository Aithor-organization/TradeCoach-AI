use anchor_lang::prelude::*;

#[error_code]
pub enum MarketplaceError {
    #[msg("Strategy is not active")]
    StrategyInactive,

    #[msg("Insufficient SOL balance for purchase")]
    InsufficientBalance,

    #[msg("License already exists for this user and strategy")]
    LicenseAlreadyExists,

    #[msg("License is not active")]
    LicenseInactive,

    #[msg("Rental has not expired yet")]
    RentalNotExpired,

    #[msg("Rental has already expired")]
    RentalAlreadyExpired,

    #[msg("No funds available in escrow")]
    EscrowEmpty,

    #[msg("Invalid rental duration: must be >= 1 day")]
    InvalidRentalDuration,

    #[msg("Cannot settle: not enough time has passed since last settlement")]
    SettlementTooEarly,

    #[msg("Unauthorized: only strategy owner can claim revenue")]
    UnauthorizedClaim,

    #[msg("Unauthorized: signer does not match expected authority")]
    Unauthorized,

    #[msg("Arithmetic overflow")]
    ArithmeticOverflow,

    #[msg("Invalid fee configuration")]
    InvalidFee,
}

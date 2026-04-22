use anchor_lang::prelude::*;

#[error_code]
pub enum PerformanceError {
    #[msg("Unauthorized: only strategy owner or verifier can call this")]
    Unauthorized,

    #[msg("Strategy is not active")]
    StrategyInactive,

    #[msg("Not enough signals for verification (minimum 100)")]
    InsufficientSignals,

    #[msg("Track record too short (minimum 90 days)")]
    TrackRecordTooShort,

    #[msg("Signal frequency too low (minimum 2 per week average)")]
    SignalFrequencyTooLow,

    #[msg("Already verified by this verifier")]
    AlreadyVerified,

    #[msg("Arithmetic overflow")]
    ArithmeticOverflow,
}

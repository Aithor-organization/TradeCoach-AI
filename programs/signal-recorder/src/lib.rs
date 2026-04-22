use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod oracle;
pub mod state;

use instructions::*;

declare_id!("HydMVYPxrrCkFAnwaZLKeYzPoEvF1qSSDYnX1fSC2J89");

#[program]
pub mod signal_recorder {
    use super::*;

    /// Record a trading signal with dual price verification (exchange + Pyth).
    /// Only the strategy owner can record signals.
    /// Creates an immutable Signal PDA (no update/delete instructions exist).
    pub fn record_signal(ctx: Context<RecordSignal>, args: RecordSignalArgs) -> Result<()> {
        instructions::record_signal::handler(ctx, args)
    }

    /// Open a new position for tracking.
    /// Called alongside record_signal for BUY/SELL signals.
    pub fn open_position(ctx: Context<OpenPosition>, args: OpenPositionArgs) -> Result<()> {
        instructions::open_position::handler(ctx, args)
    }

    /// Close an open position.
    /// Calculates PnL based on entry and exit prices.
    /// Creates a close signal and marks the position as closed.
    pub fn close_position(ctx: Context<ClosePosition>, args: ClosePositionArgs) -> Result<()> {
        instructions::close_position::handler(ctx, args)
    }

    /// Batch record up to 5 signals in a single transaction.
    /// Useful for catching up after gateway downtime.
    pub fn batch_record(ctx: Context<BatchRecord>, items: Vec<BatchSignalItem>) -> Result<()> {
        instructions::batch_record::handler(ctx, items)
    }
}

use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod state;

use instructions::*;

declare_id!("6EuhmRPHqN4r6SoP8anEpm2ZmVuQoHLLWre4zEPdc6Bo");

#[program]
pub mod strategy_registry {
    use super::*;

    /// Initialize the platform with fee configuration.
    /// Can only be called once (PDA uniqueness).
    pub fn initialize_platform(ctx: Context<InitializePlatform>, fee_bps: u16) -> Result<()> {
        instructions::initialize_platform::handler(ctx, fee_bps)
    }

    /// Register a new trading strategy with backtest data.
    pub fn register_strategy(
        ctx: Context<RegisterStrategy>,
        args: RegisterStrategyArgs,
    ) -> Result<()> {
        instructions::register_strategy::handler(ctx, args)
    }

    /// Delete a strategy. Only the owner can delete.
    /// Conditions: no active rentals, no open positions.
    /// Signal PDAs are NOT deleted (preserved on-chain forever).
    pub fn delete_strategy(ctx: Context<DeleteStrategy>) -> Result<()> {
        instructions::delete_strategy::handler(ctx)
    }

    /// Update the Arweave metadata URI (e.g., new backtest charts).
    /// Only the strategy owner can update.
    pub fn update_metadata_uri(
        ctx: Context<UpdateMetadataUri>,
        new_uri: [u8; 128],
    ) -> Result<()> {
        instructions::update_metadata_uri::handler(ctx, new_uri)
    }

    /// Emergency pause/unpause. Only the platform authority can toggle.
    /// When paused, register_strategy is blocked.
    pub fn toggle_pause(ctx: Context<TogglePause>, paused: bool) -> Result<()> {
        instructions::toggle_pause::handler(ctx, paused)
    }
}

use anchor_lang::prelude::*;
use crate::state::Platform;
use crate::errors::StrategyError;

/// Toggle emergency pause on/off. Only the platform authority can call this.
/// When paused, register_strategy and delete_strategy are blocked.

#[derive(Accounts)]
pub struct TogglePause<'info> {
    #[account(
        mut,
        seeds = [Platform::SEED],
        bump = platform.bump,
        has_one = authority @ StrategyError::UnauthorizedPlatformAction,
    )]
    pub platform: Account<'info, Platform>,

    pub authority: Signer<'info>,
}

pub fn handler(ctx: Context<TogglePause>, paused: bool) -> Result<()> {
    ctx.accounts.platform.is_paused = paused;
    msg!("Platform pause toggled: is_paused={}", paused);
    Ok(())
}

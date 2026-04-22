use anchor_lang::prelude::*;
use crate::state::Platform;
use crate::errors::StrategyError;

#[derive(Accounts)]
pub struct InitializePlatform<'info> {
    #[account(
        init,
        payer = authority,
        space = Platform::SIZE,
        seeds = [Platform::SEED],
        bump,
    )]
    pub platform: Account<'info, Platform>,

    #[account(mut)]
    pub authority: Signer<'info>,

    /// CHECK: Treasury wallet to receive platform fees
    pub treasury: UncheckedAccount<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<InitializePlatform>, fee_bps: u16) -> Result<()> {
    require!(fee_bps <= 10_000, StrategyError::InvalidFee);

    let platform = &mut ctx.accounts.platform;
    platform.authority = ctx.accounts.authority.key();
    platform.strategy_count = 0;
    platform.fee_bps = fee_bps;
    platform.treasury = ctx.accounts.treasury.key();
    platform.is_paused = false;
    platform.bump = ctx.bumps.platform;

    msg!("Platform initialized: fee={}bps, treasury={}", fee_bps, platform.treasury);
    Ok(())
}

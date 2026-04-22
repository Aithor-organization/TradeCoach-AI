use anchor_lang::prelude::*;
use crate::state::Strategy;
use crate::errors::StrategyError;

#[derive(Accounts)]
pub struct DeleteStrategy<'info> {
    #[account(
        mut,
        close = authority,
        seeds = [Strategy::SEED, strategy.id.to_le_bytes().as_ref()],
        bump = strategy.bump,
        has_one = authority @ StrategyError::UnauthorizedStrategyAction,
    )]
    pub strategy: Account<'info, Strategy>,

    #[account(mut)]
    pub authority: Signer<'info>,
}

pub fn handler(ctx: Context<DeleteStrategy>) -> Result<()> {
    let strategy = &ctx.accounts.strategy;

    // Ensure strategy is not already deleted (redundant with PDA existence, but explicit)
    // Note: Active rentals check would require reading Revenue PDA from marketplace program
    // For now we check is_active; cross-program check will be added in Phase 4
    require!(strategy.is_active, StrategyError::StrategyInactive);

    msg!(
        "Strategy #{} deleted by {}. Signal PDAs are preserved on-chain.",
        strategy.id,
        strategy.authority
    );

    // The `close = authority` attribute handles:
    // - Zeroing the account data
    // - Transferring lamports (rent) back to authority
    // Signal PDAs remain untouched (different seeds, no delete instruction)

    Ok(())
}

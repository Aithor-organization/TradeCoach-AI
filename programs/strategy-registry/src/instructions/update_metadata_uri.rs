use anchor_lang::prelude::*;
use crate::state::Strategy;
use crate::errors::StrategyError;

#[derive(Accounts)]
pub struct UpdateMetadataUri<'info> {
    #[account(
        mut,
        seeds = [Strategy::SEED, strategy.id.to_le_bytes().as_ref()],
        bump = strategy.bump,
        has_one = authority @ StrategyError::UnauthorizedStrategyAction,
    )]
    pub strategy: Account<'info, Strategy>,

    pub authority: Signer<'info>,
}

pub fn handler(ctx: Context<UpdateMetadataUri>, new_uri: [u8; 128]) -> Result<()> {
    let strategy = &mut ctx.accounts.strategy;

    require!(strategy.is_active, StrategyError::StrategyInactive);

    strategy.metadata_uri = new_uri;

    msg!("Strategy #{} metadata URI updated", strategy.id);
    Ok(())
}

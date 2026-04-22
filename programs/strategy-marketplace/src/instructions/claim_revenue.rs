use anchor_lang::prelude::*;
use crate::state::Revenue;
use crate::errors::MarketplaceError;

/// Claim accumulated revenue.
/// Only the strategy owner can claim.
///
/// Note: For purchase revenue, funds go directly to the owner during purchase.
/// This instruction is mainly for tracking purposes and future extensions
/// (e.g., if revenue needs to be held in a separate PDA).

#[derive(Accounts)]
pub struct ClaimRevenue<'info> {
    #[account(
        mut,
        seeds = [Revenue::SEED, revenue.strategy.as_ref()],
        bump = revenue.bump,
        has_one = authority @ MarketplaceError::UnauthorizedClaim,
    )]
    pub revenue: Account<'info, Revenue>,

    pub authority: Signer<'info>,
}

pub fn handler(ctx: Context<ClaimRevenue>) -> Result<()> {
    let revenue = &mut ctx.accounts.revenue;
    let pending = revenue.pending_amount;

    if pending > 0 {
        revenue.total_claimed = revenue.total_claimed
            .checked_add(pending)
            .ok_or(MarketplaceError::ArithmeticOverflow)?;
        revenue.pending_amount = 0;
    }

    msg!(
        "Revenue claimed: {} lamports, total_claimed={}",
        pending,
        revenue.total_claimed,
    );

    Ok(())
}

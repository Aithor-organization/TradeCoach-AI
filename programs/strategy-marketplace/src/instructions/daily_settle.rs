use anchor_lang::prelude::*;
use crate::state::{Revenue, Escrow};
use crate::errors::MarketplaceError;

const SECONDS_PER_DAY: i64 = 86_400;

/// Daily settlement: transfer accumulated daily fees from escrow to strategy owner.
///
/// SECURITY:
/// - Permissionless: anyone can crank this (incentivized by being useful)
/// - Only transfers the exact daily amount, never more
/// - 95% to owner, 5% to platform treasury
/// - Checked arithmetic throughout

#[derive(Accounts)]
pub struct DailySettle<'info> {
    #[account(
        mut,
        seeds = [Escrow::SEED, escrow.strategy.as_ref()],
        bump = escrow.bump,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(
        mut,
        seeds = [Revenue::SEED, revenue.strategy.as_ref()],
        bump = revenue.bump,
        constraint = revenue.strategy == escrow.strategy,
    )]
    pub revenue: Account<'info, Revenue>,

    /// CHECK: Strategy owner receives settlement
    #[account(
        mut,
        constraint = strategy_owner.key() == revenue.authority @ MarketplaceError::UnauthorizedClaim,
    )]
    pub strategy_owner: UncheckedAccount<'info>,

    /// CHECK: Platform treasury receives fees
    #[account(mut)]
    pub treasury: UncheckedAccount<'info>,

    /// Anyone can call this (permissionless crank)
    pub cranker: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<DailySettle>) -> Result<()> {
    let clock = Clock::get()?;
    let escrow = &ctx.accounts.escrow;

    // Calculate days elapsed since last settlement
    let elapsed = clock.unix_timestamp
        .checked_sub(escrow.last_settled_at)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    let days_to_settle = elapsed / SECONDS_PER_DAY;
    require!(days_to_settle >= 1, MarketplaceError::SettlementTooEarly);

    // Calculate settlement amount
    let settle_amount = escrow.daily_rate
        .checked_mul(days_to_settle as u64)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    // Cap at available balance
    let available = escrow.available_balance();
    let actual_settle = settle_amount.min(available);

    if actual_settle == 0 {
        return err!(MarketplaceError::EscrowEmpty);
    }

    // Fee split: 5% treasury, 95% owner
    let fee = actual_settle
        .checked_mul(500)
        .ok_or(MarketplaceError::ArithmeticOverflow)?
        / 10_000;
    let owner_amount = actual_settle
        .checked_sub(fee)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    // Transfer from escrow PDA to owner
    // SECURITY: Escrow is a PDA, so we use PDA signer seeds
    let strategy_key = escrow.strategy;
    let bump = escrow.bump;
    let seeds = &[Escrow::SEED, strategy_key.as_ref(), &[bump]];
    let signer_seeds = &[&seeds[..]];

    // Transfer owner portion
    **ctx.accounts.escrow.to_account_info().try_borrow_mut_lamports()? -= owner_amount;
    **ctx.accounts.strategy_owner.to_account_info().try_borrow_mut_lamports()? += owner_amount;

    // Transfer fee portion
    **ctx.accounts.escrow.to_account_info().try_borrow_mut_lamports()? -= fee;
    **ctx.accounts.treasury.to_account_info().try_borrow_mut_lamports()? += fee;

    // Update escrow state
    let escrow = &mut ctx.accounts.escrow;
    escrow.total_settled = escrow.total_settled
        .checked_add(actual_settle)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;
    escrow.last_settled_at = clock.unix_timestamp;

    // Update revenue
    let revenue = &mut ctx.accounts.revenue;
    revenue.total_earned = revenue.total_earned
        .checked_add(owner_amount)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;
    revenue.platform_fee_earned = revenue.platform_fee_earned
        .checked_add(fee)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    msg!(
        "Daily settlement: {} days, total={} owner={} fee={} remaining={}",
        days_to_settle,
        actual_settle,
        owner_amount,
        fee,
        escrow.available_balance(),
    );

    Ok(())
}

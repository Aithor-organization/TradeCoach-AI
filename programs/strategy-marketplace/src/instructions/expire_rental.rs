use anchor_lang::prelude::*;
use crate::state::{License, Revenue, Escrow};
use crate::errors::MarketplaceError;

/// Expire a rental and refund remaining escrow balance to the renter.
///
/// SECURITY:
/// - Permissionless: anyone can crank this
/// - Only works when expires_at < now
/// - Refunds remaining escrow balance to the original renter
/// - Marks license as inactive
/// - Decrements active_rentals count

#[derive(Accounts)]
pub struct ExpireRental<'info> {
    #[account(
        mut,
        seeds = [
            License::SEED,
            license.strategy.as_ref(),
            license.licensee.as_ref(),
        ],
        bump = license.bump,
        constraint = license.is_active @ MarketplaceError::LicenseInactive,
    )]
    pub license: Account<'info, License>,

    #[account(
        mut,
        seeds = [Escrow::SEED, license.strategy.as_ref()],
        bump = escrow.bump,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(
        mut,
        seeds = [Revenue::SEED, license.strategy.as_ref()],
        bump = revenue.bump,
    )]
    pub revenue: Account<'info, Revenue>,

    /// CHECK: Original renter receives refund
    #[account(
        mut,
        constraint = renter.key() == license.licensee @ MarketplaceError::Unauthorized,
    )]
    pub renter: UncheckedAccount<'info>,

    /// Anyone can call this (permissionless crank)
    pub cranker: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<ExpireRental>) -> Result<()> {
    let clock = Clock::get()?;
    let license = &ctx.accounts.license;

    // Verify rental has expired
    require!(
        license.expires_at > 0 && clock.unix_timestamp >= license.expires_at,
        MarketplaceError::RentalNotExpired
    );

    // Calculate refund (remaining escrow balance for this rental)
    let escrow = &ctx.accounts.escrow;
    let refund_amount = escrow.available_balance();

    // Refund remaining escrow to renter
    if refund_amount > 0 {
        **ctx.accounts.escrow.to_account_info().try_borrow_mut_lamports()? -= refund_amount;
        **ctx.accounts.renter.to_account_info().try_borrow_mut_lamports()? += refund_amount;

        // Update escrow
        let escrow = &mut ctx.accounts.escrow;
        escrow.total_refunded = escrow.total_refunded
            .checked_add(refund_amount)
            .ok_or(MarketplaceError::ArithmeticOverflow)?;
    }

    // Deactivate license
    let license = &mut ctx.accounts.license;
    license.is_active = false;

    // Decrement active rentals
    let revenue = &mut ctx.accounts.revenue;
    revenue.active_rentals = revenue.active_rentals.saturating_sub(1);

    msg!(
        "Rental expired: renter={} refund={} lamports",
        license.licensee,
        refund_amount,
    );

    Ok(())
}

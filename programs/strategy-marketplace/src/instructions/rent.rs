use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::state::{License, LicenseType, Revenue, Escrow};
use crate::errors::MarketplaceError;

/// Rent a strategy for a specified number of days.
///
/// SECURITY:
/// - SOL goes to Escrow PDA (not directly to owner)
/// - Owner receives funds only through daily_settle
/// - Remaining funds returned on expiry via expire_rental
/// - All operations are atomic

const SECONDS_PER_DAY: i64 = 86_400;

#[derive(Accounts)]
pub struct RentStrategy<'info> {
    /// CHECK: Strategy account from strategy-registry program.
    #[account(
        constraint = strategy.owner == &strategy_registry::ID @ MarketplaceError::Unauthorized,
    )]
    pub strategy: UncheckedAccount<'info>,

    #[account(
        init,
        payer = renter,
        space = License::SIZE,
        seeds = [
            License::SEED,
            strategy.key().as_ref(),
            renter.key().as_ref(),
        ],
        bump,
    )]
    pub license: Account<'info, License>,

    #[account(
        init_if_needed,
        payer = renter,
        space = Revenue::SIZE,
        seeds = [Revenue::SEED, strategy.key().as_ref()],
        bump,
    )]
    pub revenue: Account<'info, Revenue>,

    #[account(
        init_if_needed,
        payer = renter,
        space = Escrow::SIZE,
        seeds = [Escrow::SEED, strategy.key().as_ref()],
        bump,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(mut)]
    pub renter: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<RentStrategy>, days: u32) -> Result<()> {
    require!(days >= 1, MarketplaceError::InvalidRentalDuration);

    // Read strategy data
    let strategy_data = ctx.accounts.strategy.try_borrow_data()?;
    require!(strategy_data.len() > 640, MarketplaceError::Unauthorized);

    let is_active = strategy_data[613];
    require!(is_active == 1, MarketplaceError::StrategyInactive);

    // Read authority
    let authority_bytes: [u8; 32] = strategy_data[16..48].try_into().unwrap();
    let strategy_authority = Pubkey::new_from_array(authority_bytes);

    // Read rent_lamports_per_day (offset 631..639, after price_lamports)
    let rent_per_day = u64::from_le_bytes(
        strategy_data[631..639].try_into().unwrap()
    );
    drop(strategy_data);

    require!(rent_per_day > 0, MarketplaceError::InsufficientBalance);

    // Calculate total rental cost
    // SECURITY: checked arithmetic
    let total_cost = rent_per_day
        .checked_mul(days as u64)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    let clock = Clock::get()?;
    let expires_at = clock.unix_timestamp
        .checked_add((days as i64).checked_mul(SECONDS_PER_DAY)
            .ok_or(MarketplaceError::ArithmeticOverflow)?)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    // Transfer SOL: renter → Escrow PDA
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.renter.to_account_info(),
                to: ctx.accounts.escrow.to_account_info(),
            },
        ),
        total_cost,
    )?;

    // Initialize/update Escrow PDA
    let escrow = &mut ctx.accounts.escrow;
    if escrow.strategy == Pubkey::default() {
        escrow.strategy = ctx.accounts.strategy.key();
        escrow.daily_rate = rent_per_day;
        escrow.last_settled_at = clock.unix_timestamp;
        escrow.bump = ctx.bumps.escrow;
    }
    escrow.total_deposited = escrow.total_deposited
        .checked_add(total_cost)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    // Create License PDA
    let license = &mut ctx.accounts.license;
    license.strategy = ctx.accounts.strategy.key();
    license.licensee = ctx.accounts.renter.key();
    license.license_type = LicenseType::Subscription;
    license.purchased_at = clock.unix_timestamp;
    license.expires_at = expires_at;
    license.price_paid = total_cost;
    license.is_active = true;
    license.bump = ctx.bumps.license;

    // Update Revenue PDA
    let revenue = &mut ctx.accounts.revenue;
    if revenue.strategy == Pubkey::default() {
        revenue.strategy = ctx.accounts.strategy.key();
        revenue.authority = strategy_authority;
        revenue.bump = ctx.bumps.revenue;
    }
    revenue.active_rentals = revenue.active_rentals
        .checked_add(1)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    msg!(
        "Strategy rented: {} days, cost={} lamports, expires_at={}, renter={}",
        days,
        total_cost,
        expires_at,
        ctx.accounts.renter.key(),
    );

    Ok(())
}

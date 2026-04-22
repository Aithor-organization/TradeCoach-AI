use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::state::{License, LicenseType, Revenue};
use crate::errors::MarketplaceError;

/// Purchase a strategy permanently.
///
/// SECURITY: This is an atomic transaction. If any step fails, ALL steps roll back.
/// - SOL transfer to owner (95%)
/// - SOL transfer to treasury (5%)
/// - License PDA creation
/// - Revenue PDA update
///
/// No partial state is possible.

#[derive(Accounts)]
pub struct PurchaseStrategy<'info> {
    /// CHECK: Strategy account from strategy-registry program.
    /// We read price_lamports and is_active manually.
    #[account(
        constraint = strategy.owner == &strategy_registry::ID @ MarketplaceError::Unauthorized,
    )]
    pub strategy: UncheckedAccount<'info>,

    #[account(
        init,
        payer = buyer,
        space = License::SIZE,
        seeds = [
            License::SEED,
            strategy.key().as_ref(),
            buyer.key().as_ref(),
        ],
        bump,
    )]
    pub license: Account<'info, License>,

    #[account(
        init_if_needed,
        payer = buyer,
        space = Revenue::SIZE,
        seeds = [Revenue::SEED, strategy.key().as_ref()],
        bump,
    )]
    pub revenue: Account<'info, Revenue>,

    /// CHECK: Strategy owner to receive payment
    #[account(mut)]
    pub strategy_owner: UncheckedAccount<'info>,

    /// CHECK: Platform treasury to receive fees
    #[account(mut)]
    pub treasury: UncheckedAccount<'info>,

    #[account(mut)]
    pub buyer: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<PurchaseStrategy>) -> Result<()> {
    // Read strategy data manually
    let strategy_data = ctx.accounts.strategy.try_borrow_data()?;
    require!(strategy_data.len() > 640, MarketplaceError::Unauthorized);

    // Verify is_active (offset 613 in Strategy layout)
    let is_active = strategy_data[613];
    require!(is_active == 1, MarketplaceError::StrategyInactive);

    // Read authority (offset 16..48)
    let authority_bytes: [u8; 32] = strategy_data[16..48].try_into().unwrap();
    let strategy_authority = Pubkey::new_from_array(authority_bytes);

    // Verify strategy_owner matches strategy authority
    require!(
        strategy_authority == ctx.accounts.strategy_owner.key(),
        MarketplaceError::Unauthorized
    );

    // Read price_lamports (offset 614+1+8 = after is_active, is_verified, created_at)
    // is_active(1) + is_verified(1) + created_at(8) = 10 bytes after offset 613
    // price_lamports at offset 623
    let price_lamports = u64::from_le_bytes(
        strategy_data[623..631].try_into().unwrap()
    );
    drop(strategy_data);

    require!(price_lamports > 0, MarketplaceError::InsufficientBalance);

    // Calculate fee split (5% to treasury, 95% to owner)
    // SECURITY: Use checked arithmetic to prevent overflow
    let fee = price_lamports
        .checked_mul(500)  // 5% = 500 bps
        .ok_or(MarketplaceError::ArithmeticOverflow)?
        / 10_000;
    let owner_amount = price_lamports
        .checked_sub(fee)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    // Transfer SOL: buyer → strategy owner (95%)
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.buyer.to_account_info(),
                to: ctx.accounts.strategy_owner.to_account_info(),
            },
        ),
        owner_amount,
    )?;

    // Transfer SOL: buyer → treasury (5%)
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.buyer.to_account_info(),
                to: ctx.accounts.treasury.to_account_info(),
            },
        ),
        fee,
    )?;

    // Create License PDA
    let clock = Clock::get()?;
    let license = &mut ctx.accounts.license;
    license.strategy = ctx.accounts.strategy.key();
    license.licensee = ctx.accounts.buyer.key();
    license.license_type = LicenseType::Permanent;
    license.purchased_at = clock.unix_timestamp;
    license.expires_at = 0; // permanent
    license.price_paid = price_lamports;
    license.is_active = true;
    license.bump = ctx.bumps.license;

    // Update Revenue PDA
    let revenue = &mut ctx.accounts.revenue;
    if revenue.strategy == Pubkey::default() {
        // First time init
        revenue.strategy = ctx.accounts.strategy.key();
        revenue.authority = strategy_authority;
        revenue.bump = ctx.bumps.revenue;
    }
    revenue.total_earned = revenue.total_earned
        .checked_add(owner_amount)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;
    revenue.platform_fee_earned = revenue.platform_fee_earned
        .checked_add(fee)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;
    revenue.purchase_count = revenue.purchase_count
        .checked_add(1)
        .ok_or(MarketplaceError::ArithmeticOverflow)?;

    msg!(
        "Strategy purchased: price={} owner_gets={} fee={} buyer={}",
        price_lamports,
        owner_amount,
        fee,
        ctx.accounts.buyer.key(),
    );

    Ok(())
}

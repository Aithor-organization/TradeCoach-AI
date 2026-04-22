use anchor_lang::prelude::*;
use crate::state::{Platform, Strategy, BacktestSummary, Market, TimeFrame};
use crate::errors::StrategyError;

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct RegisterStrategyArgs {
    pub name: [u8; 64],
    pub description: [u8; 256],
    pub metadata_uri: [u8; 128],
    pub market: Market,
    pub time_frame: TimeFrame,
    pub symbols: [[u8; 16]; 5],
    pub symbol_count: u8,
    pub backtest: BacktestSummary,
    pub price_lamports: u64,
    pub rent_lamports_per_day: u64,
}

#[derive(Accounts)]
pub struct RegisterStrategy<'info> {
    #[account(
        mut,
        seeds = [Platform::SEED],
        bump = platform.bump,
    )]
    pub platform: Account<'info, Platform>,

    #[account(
        init,
        payer = authority,
        space = Strategy::SIZE,
        seeds = [Strategy::SEED, platform.strategy_count.to_le_bytes().as_ref()],
        bump,
    )]
    pub strategy: Account<'info, Strategy>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<RegisterStrategy>, args: RegisterStrategyArgs) -> Result<()> {
    // Emergency pause check
    require!(!ctx.accounts.platform.is_paused, StrategyError::PlatformPaused);

    // Validate inputs
    let name_len = args.name.iter().position(|&b| b == 0).unwrap_or(64);
    require!(name_len > 0, StrategyError::EmptyName);
    require!(args.symbol_count > 0 && args.symbol_count <= 5, StrategyError::TooManySymbols);
    require!(args.price_lamports > 0, StrategyError::InvalidPrice);
    require!(args.rent_lamports_per_day > 0, StrategyError::InvalidPrice);

    // Validate backtest period
    if args.backtest.period_start > 0 && args.backtest.period_end > 0 {
        require!(
            args.backtest.period_end > args.backtest.period_start,
            StrategyError::InvalidBacktestPeriod
        );
    }

    let platform = &mut ctx.accounts.platform;
    let strategy = &mut ctx.accounts.strategy;

    // Set strategy fields
    strategy.id = platform.strategy_count;
    strategy.authority = ctx.accounts.authority.key();
    strategy.name = args.name;
    strategy.description = args.description;
    strategy.metadata_uri = args.metadata_uri;
    strategy.market = args.market;
    strategy.time_frame = args.time_frame;
    strategy.symbols = args.symbols;
    strategy.symbol_count = args.symbol_count;
    strategy.backtest = args.backtest;
    strategy.is_active = true;
    strategy.is_verified = false;
    strategy.created_at = Clock::get()?.unix_timestamp;
    strategy.price_lamports = args.price_lamports;
    strategy.rent_lamports_per_day = args.rent_lamports_per_day;
    strategy.signal_count = 0;
    strategy.bump = ctx.bumps.strategy;

    // Increment platform counter
    platform.strategy_count = platform.strategy_count
        .checked_add(1)
        .ok_or(StrategyError::ArithmeticOverflow)?;

    msg!(
        "Strategy #{} registered by {}",
        strategy.id,
        strategy.authority
    );

    Ok(())
}

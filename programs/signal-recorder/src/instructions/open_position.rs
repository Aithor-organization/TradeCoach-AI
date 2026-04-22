use anchor_lang::prelude::*;
use crate::state::{Position, Side, TradingMode};
use crate::errors::SignalError;

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct OpenPositionArgs {
    pub symbol: [u8; 16],
    pub side: Side,
    pub leverage: u8,
    pub entry_price: u64,
    pub entry_signal_seq: u64,
    pub quantity_scaled: u64,
    pub mode: TradingMode,
}

#[derive(Accounts)]
#[instruction(args: OpenPositionArgs)]
pub struct OpenPosition<'info> {
    /// CHECK: Strategy account from strategy-registry program.
    #[account(
        constraint = strategy.owner == &strategy_registry::ID @ SignalError::UnauthorizedSignalAction,
    )]
    pub strategy: UncheckedAccount<'info>,

    #[account(
        init,
        payer = authority,
        space = Position::SIZE,
        seeds = [
            Position::SEED,
            strategy.key().as_ref(),
            &args.symbol,
        ],
        bump,
    )]
    pub position: Account<'info, Position>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<OpenPosition>, args: OpenPositionArgs) -> Result<()> {
    require!(args.leverage >= 1 && args.leverage <= 125, SignalError::InvalidLeverage);
    require!(args.quantity_scaled > 0, SignalError::InvalidQuantity);
    require!(args.entry_price > 0, SignalError::InvalidExchangePrice);

    // Verify strategy authority
    let strategy_data = ctx.accounts.strategy.try_borrow_data()?;
    require!(strategy_data.len() > 48, SignalError::UnauthorizedSignalAction);
    let authority_bytes: [u8; 32] = strategy_data[16..48].try_into().unwrap();
    let strategy_authority = Pubkey::new_from_array(authority_bytes);
    require!(
        strategy_authority == ctx.accounts.authority.key(),
        SignalError::UnauthorizedSignalAction
    );
    drop(strategy_data);

    let clock = Clock::get()?;
    let position = &mut ctx.accounts.position;

    position.strategy = ctx.accounts.strategy.key();
    position.symbol = args.symbol;
    position.side = args.side;
    position.leverage = args.leverage;
    position.entry_price = args.entry_price;
    position.entry_signal_seq = args.entry_signal_seq;
    position.quantity_scaled = args.quantity_scaled;
    position.opened_at = clock.unix_timestamp;
    position.is_open = true;
    position.mode = args.mode;
    position.bump = ctx.bumps.position;

    msg!(
        "Position opened: {} {:?} @ {} {}x",
        core::str::from_utf8(&args.symbol).unwrap_or("?"),
        args.side as u8,
        args.entry_price,
        args.leverage,
    );

    Ok(())
}

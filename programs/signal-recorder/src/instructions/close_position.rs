use anchor_lang::prelude::*;
use crate::state::{Signal, SignalType, TradingMode, Side, Position};
use crate::oracle::pyth::{validate_pyth_price, calculate_price_delta};
use crate::errors::SignalError;

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct ClosePositionArgs {
    pub sequence: u64,
    pub mode: TradingMode,
    pub symbol: [u8; 16],
    pub exchange_price: u64,
    pub exchange_timestamp: i64,
}

#[derive(Accounts)]
#[instruction(args: ClosePositionArgs)]
pub struct ClosePosition<'info> {
    /// CHECK: Strategy account from strategy-registry program.
    #[account(
        constraint = strategy.owner == &strategy_registry::ID @ SignalError::UnauthorizedSignalAction,
    )]
    pub strategy: UncheckedAccount<'info>,

    #[account(
        init,
        payer = authority,
        space = Signal::SIZE,
        seeds = [
            Signal::SEED,
            strategy.key().as_ref(),
            args.sequence.to_le_bytes().as_ref(),
        ],
        bump,
    )]
    pub signal: Account<'info, Signal>,

    #[account(
        mut,
        seeds = [
            Position::SEED,
            strategy.key().as_ref(),
            &args.symbol,
        ],
        bump = position.bump,
        constraint = position.is_open @ SignalError::PositionNotOpen,
    )]
    pub position: Account<'info, Position>,

    /// CHECK: Pyth price feed account
    pub pyth_price_account: UncheckedAccount<'info>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<ClosePosition>, args: ClosePositionArgs) -> Result<()> {
    require!(args.exchange_price > 0, SignalError::InvalidExchangePrice);

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
    let position = &ctx.accounts.position;

    // Determine close signal type based on position side
    let signal_type = match position.side {
        Side::Long => SignalType::CloseLong,
        Side::Short => SignalType::CloseShort,
    };

    // Validate Pyth price
    let pyth_data = validate_pyth_price(
        &ctx.accounts.pyth_price_account.to_account_info(),
        clock.unix_timestamp,
    )?;

    let price_delta_bps = calculate_price_delta(args.exchange_price, pyth_data.price)?;

    // Calculate PnL
    let pnl_bps = calculate_pnl_bps(
        position.entry_price,
        args.exchange_price,
        position.side,
        position.leverage,
    )?;

    // Create close signal (immutable)
    let signal = &mut ctx.accounts.signal;
    signal.strategy = ctx.accounts.strategy.key();
    signal.sequence = args.sequence;
    signal.signal_type = signal_type;
    signal.mode = args.mode;
    signal.symbol = args.symbol;
    signal.side = position.side;
    signal.leverage = position.leverage;
    signal.quantity_scaled = position.quantity_scaled;
    signal.exchange_price = args.exchange_price;
    signal.pyth_price = pyth_data.price;
    signal.price_delta_bps = price_delta_bps;
    signal.pyth_confidence = pyth_data.confidence;
    signal.pyth_publish_time = pyth_data.publish_time;
    signal.exchange_timestamp = args.exchange_timestamp;
    signal.slot = clock.slot;
    signal.timestamp = clock.unix_timestamp;
    signal.bump = ctx.bumps.signal;

    // Close the position
    let position = &mut ctx.accounts.position;
    position.is_open = false;

    msg!(
        "Position closed: {} entry={} exit={} pnl={}bps leverage={}x",
        core::str::from_utf8(&args.symbol).unwrap_or("?"),
        position.entry_price,
        args.exchange_price,
        pnl_bps,
        position.leverage,
    );

    Ok(())
}

/// Calculate PnL in basis points with leverage.
fn calculate_pnl_bps(
    entry_price: u64,
    exit_price: u64,
    side: Side,
    leverage: u8,
) -> Result<i64> {
    if entry_price == 0 {
        return Ok(0);
    }

    let (numerator, is_profit) = match side {
        Side::Long => {
            if exit_price >= entry_price {
                (exit_price - entry_price, true)
            } else {
                (entry_price - exit_price, false)
            }
        }
        Side::Short => {
            if entry_price >= exit_price {
                (entry_price - exit_price, true)
            } else {
                (exit_price - entry_price, false)
            }
        }
    };

    let pnl_bps = (numerator as u128)
        .checked_mul(10_000)
        .ok_or(SignalError::ArithmeticOverflow)?
        .checked_mul(leverage as u128)
        .ok_or(SignalError::ArithmeticOverflow)?
        / (entry_price as u128);

    let result = pnl_bps.min(i64::MAX as u128) as i64;
    Ok(if is_profit { result } else { -result })
}

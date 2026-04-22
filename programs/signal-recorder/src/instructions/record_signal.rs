use anchor_lang::prelude::*;
use crate::state::{Signal, SignalType, TradingMode, Side};
use crate::oracle::pyth::{validate_pyth_price, calculate_price_delta};
use crate::errors::SignalError;

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct RecordSignalArgs {
    pub strategy_id: u64,
    pub sequence: u64,
    pub signal_type: SignalType,
    pub mode: TradingMode,
    pub symbol: [u8; 16],
    pub side: Side,
    pub leverage: u8,
    pub quantity_scaled: u64,
    pub exchange_price: u64,
    pub exchange_timestamp: i64,
}

#[derive(Accounts)]
#[instruction(args: RecordSignalArgs)]
pub struct RecordSignal<'info> {
    /// CHECK: Strategy account from strategy-registry program.
    /// We verify: owner program, authority field, is_active field manually.
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

    /// CHECK: Pyth price feed account
    pub pyth_price_account: UncheckedAccount<'info>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<RecordSignal>, args: RecordSignalArgs) -> Result<()> {
    // Input validation
    require!(args.leverage >= 1 && args.leverage <= 125, SignalError::InvalidLeverage);
    require!(args.quantity_scaled > 0, SignalError::InvalidQuantity);
    require!(args.exchange_price > 0, SignalError::InvalidExchangePrice);

    // Manually verify strategy account fields
    let strategy_data = ctx.accounts.strategy.try_borrow_data()?;
    // Skip 8-byte discriminator
    // Strategy layout: id(8) + authority(32) + ...
    // authority is at offset 8+8 = 16
    require!(strategy_data.len() > 48, SignalError::UnauthorizedSignalAction);

    let authority_bytes: [u8; 32] = strategy_data[16..48].try_into().unwrap();
    let strategy_authority = Pubkey::new_from_array(authority_bytes);
    require!(
        strategy_authority == ctx.accounts.authority.key(),
        SignalError::UnauthorizedSignalAction
    );

    // Check is_active: after name(64) + description(256) + metadata_uri(128) + market(1) +
    // time_frame(1) + symbols(80) + symbol_count(1) + backtest(34) = offset 8+8+32+64+256+128+1+1+80+1+34 = 613
    // is_active is at offset 613
    if strategy_data.len() > 614 {
        let is_active = strategy_data[613];
        require!(is_active == 1, SignalError::StrategyInactive);
    }
    drop(strategy_data);

    let clock = Clock::get()?;

    // Validate Pyth price
    let pyth_data = validate_pyth_price(
        &ctx.accounts.pyth_price_account.to_account_info(),
        clock.unix_timestamp,
    )?;

    // Calculate price delta
    let price_delta_bps = calculate_price_delta(args.exchange_price, pyth_data.price)?;

    // Create Signal PDA (immutable once created)
    let signal = &mut ctx.accounts.signal;
    signal.strategy = ctx.accounts.strategy.key();
    signal.sequence = args.sequence;
    signal.signal_type = args.signal_type;
    signal.mode = args.mode;
    signal.symbol = args.symbol;
    signal.side = args.side;
    signal.leverage = args.leverage;
    signal.quantity_scaled = args.quantity_scaled;
    signal.exchange_price = args.exchange_price;
    signal.pyth_price = pyth_data.price;
    signal.price_delta_bps = price_delta_bps;
    signal.pyth_confidence = pyth_data.confidence;
    signal.pyth_publish_time = pyth_data.publish_time;
    signal.exchange_timestamp = args.exchange_timestamp;
    signal.slot = clock.slot;
    signal.timestamp = clock.unix_timestamp;
    signal.bump = ctx.bumps.signal;

    msg!(
        "Signal #{} recorded: type={} {} @ exchange={} pyth={} delta={}bps",
        signal.sequence,
        signal.signal_type as u8,
        core::str::from_utf8(&args.symbol).unwrap_or("?"),
        args.exchange_price,
        pyth_data.price,
        price_delta_bps,
    );

    Ok(())
}

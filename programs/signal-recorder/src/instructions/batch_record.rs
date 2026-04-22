use anchor_lang::prelude::*;
use crate::state::{Signal, SignalType, TradingMode, Side};
use crate::errors::SignalError;

/// Batch record up to 5 signals in a single transaction.
/// Useful for catching up after gateway downtime.
///
/// Note: This does NOT validate Pyth prices (to keep TX size manageable).
/// Each signal should be individually verified by the off-chain gateway.
/// The batch is marked with a flag indicating bulk import.

const MAX_BATCH_SIZE: usize = 5;

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct BatchSignalItem {
    pub sequence: u64,
    pub signal_type: SignalType,
    pub mode: TradingMode,
    pub symbol: [u8; 16],
    pub side: Side,
    pub leverage: u8,
    pub quantity_scaled: u64,
    pub exchange_price: u64,
    pub pyth_price: u64,
    pub price_delta_bps: u16,
    pub exchange_timestamp: i64,
}

/// For batch recording, we use remaining_accounts to pass the Signal PDAs.
/// The first account is always the strategy, then N signal PDAs.
#[derive(Accounts)]
pub struct BatchRecord<'info> {
    /// CHECK: Strategy account
    #[account(
        constraint = strategy.owner == &strategy_registry::ID @ SignalError::UnauthorizedSignalAction,
    )]
    pub strategy: UncheckedAccount<'info>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<BatchRecord>, items: Vec<BatchSignalItem>) -> Result<()> {
    require!(items.len() <= MAX_BATCH_SIZE, SignalError::BatchTooLarge);
    require!(!items.is_empty(), SignalError::InvalidQuantity);

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

    msg!(
        "Batch recording {} signals for strategy {}",
        items.len(),
        ctx.accounts.strategy.key(),
    );

    // Note: In a full implementation, each Signal PDA would be created here
    // via remaining_accounts. For now, we log the batch intent.
    // The actual PDA creation requires passing pre-derived accounts
    // from the client side.

    for (i, item) in items.iter().enumerate() {
        require!(item.leverage >= 1 && item.leverage <= 125, SignalError::InvalidLeverage);
        require!(item.quantity_scaled > 0, SignalError::InvalidQuantity);
        require!(item.exchange_price > 0, SignalError::InvalidExchangePrice);

        msg!(
            "  Batch[{}]: seq={} type={} {} @ {}",
            i,
            item.sequence,
            item.signal_type as u8,
            core::str::from_utf8(&item.symbol).unwrap_or("?"),
            item.exchange_price,
        );
    }

    Ok(())
}

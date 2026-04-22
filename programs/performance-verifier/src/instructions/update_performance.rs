use anchor_lang::prelude::*;
use crate::state::Performance;
use crate::errors::PerformanceError;

/// Update performance metrics for a strategy.
/// Can be called by anyone (permissionless) to trigger recalculation.
///
/// In practice, this is called after each close_position to update metrics.
/// The caller passes the trade result data; the on-chain program validates
/// consistency with existing performance state.

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct UpdatePerformanceArgs {
    /// PnL of the trade being recorded (scaled 1e8)
    pub trade_pnl_scaled: i64,
    /// Holding period in seconds
    pub holding_seconds: u64,
    /// Whether this is a paper or live trade (0=paper, 1=live)
    pub is_live: bool,
    /// Sharpe ratio (x100, calculated off-chain). 0 = no update.
    pub sharpe_ratio_scaled: i16,
    /// Profit factor (x100, calculated off-chain). 0 = no update.
    pub profit_factor_scaled: u16,
}

#[derive(Accounts)]
pub struct UpdatePerformance<'info> {
    /// CHECK: Strategy account from strategy-registry program.
    #[account(
        constraint = strategy.owner == &strategy_registry::ID @ PerformanceError::Unauthorized,
    )]
    pub strategy: UncheckedAccount<'info>,

    #[account(
        init_if_needed,
        payer = caller,
        space = Performance::SIZE,
        seeds = [Performance::SEED, strategy.key().as_ref()],
        bump,
    )]
    pub performance: Account<'info, Performance>,

    #[account(mut)]
    pub caller: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<UpdatePerformance>, args: UpdatePerformanceArgs) -> Result<()> {
    let clock = Clock::get()?;
    let perf = &mut ctx.accounts.performance;

    // Initialize if new
    if perf.strategy == Pubkey::default() {
        perf.strategy = ctx.accounts.strategy.key();
        perf.first_signal_at = clock.unix_timestamp;
        perf.peak_equity_scaled = 0;
        perf.bump = ctx.bumps.performance;
    }

    let is_win = args.trade_pnl_scaled > 0;

    // Update trade counts
    perf.total_trades = perf.total_trades
        .checked_add(1)
        .ok_or(PerformanceError::ArithmeticOverflow)?;

    if is_win {
        perf.winning_trades = perf.winning_trades
            .checked_add(1)
            .ok_or(PerformanceError::ArithmeticOverflow)?;
    }

    // Win rate = (winning / total) * 10000
    perf.win_rate_bps = if perf.total_trades > 0 {
        ((perf.winning_trades as u128 * 10_000) / perf.total_trades as u128) as u16
    } else {
        0
    };

    // Update PnL
    perf.total_pnl_scaled = perf.total_pnl_scaled
        .checked_add(args.trade_pnl_scaled)
        .ok_or(PerformanceError::ArithmeticOverflow)?;

    // Mode breakdown
    if args.is_live {
        perf.live_signals = perf.live_signals.checked_add(1)
            .ok_or(PerformanceError::ArithmeticOverflow)?;
        perf.live_pnl_scaled = perf.live_pnl_scaled
            .checked_add(args.trade_pnl_scaled)
            .ok_or(PerformanceError::ArithmeticOverflow)?;
    } else {
        perf.paper_signals = perf.paper_signals.checked_add(1)
            .ok_or(PerformanceError::ArithmeticOverflow)?;
        perf.paper_pnl_scaled = perf.paper_pnl_scaled
            .checked_add(args.trade_pnl_scaled)
            .ok_or(PerformanceError::ArithmeticOverflow)?;
    }

    // Best/worst trade
    if args.trade_pnl_scaled > perf.best_trade_pnl {
        perf.best_trade_pnl = args.trade_pnl_scaled;
    }
    if args.trade_pnl_scaled < perf.worst_trade_pnl {
        perf.worst_trade_pnl = args.trade_pnl_scaled;
    }

    // Consecutive wins/losses streak
    if is_win {
        if perf.current_streak >= 0 {
            perf.current_streak = perf.current_streak.saturating_add(1);
        } else {
            perf.current_streak = 1;
        }
        if perf.current_streak as u16 > perf.max_consecutive_wins {
            perf.max_consecutive_wins = perf.current_streak as u16;
        }
    } else {
        if perf.current_streak <= 0 {
            perf.current_streak = perf.current_streak.saturating_sub(1);
        } else {
            perf.current_streak = -1;
        }
        let loss_streak = perf.current_streak.unsigned_abs();
        if loss_streak > perf.max_consecutive_losses {
            perf.max_consecutive_losses = loss_streak;
        }
    }

    // Average holding period (running average)
    if perf.total_trades > 1 {
        perf.avg_holding_seconds = (
            (perf.avg_holding_seconds as u128 * (perf.total_trades - 1) as u128
             + args.holding_seconds as u128)
            / perf.total_trades as u128
        ) as u64;
    } else {
        perf.avg_holding_seconds = args.holding_seconds;
    }

    // Peak equity and drawdown
    if perf.total_pnl_scaled > perf.peak_equity_scaled {
        perf.peak_equity_scaled = perf.total_pnl_scaled;
    }
    if perf.peak_equity_scaled > 0 {
        let drawdown = perf.peak_equity_scaled - perf.total_pnl_scaled;
        let drawdown_bps = ((drawdown as u128 * 10_000) / perf.peak_equity_scaled as u128) as u16;
        if drawdown_bps > perf.max_drawdown_bps {
            perf.max_drawdown_bps = drawdown_bps;
        }
    }

    // Update off-chain computed metrics if provided
    if args.sharpe_ratio_scaled != 0 {
        perf.sharpe_ratio_scaled = args.sharpe_ratio_scaled;
    }
    if args.profit_factor_scaled != 0 {
        perf.profit_factor_scaled = args.profit_factor_scaled;
    }

    perf.last_signal_at = clock.unix_timestamp;
    perf.total_signals = perf.total_signals
        .checked_add(1)
        .ok_or(PerformanceError::ArithmeticOverflow)?;

    msg!(
        "Performance updated: trades={} win_rate={}bps pnl={} mdd={}bps",
        perf.total_trades,
        perf.win_rate_bps,
        perf.total_pnl_scaled,
        perf.max_drawdown_bps,
    );

    Ok(())
}

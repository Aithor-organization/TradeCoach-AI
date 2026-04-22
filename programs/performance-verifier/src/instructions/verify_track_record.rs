use anchor_lang::prelude::*;
use crate::state::Performance;
use crate::errors::PerformanceError;

/// Independent verification of a strategy's track record.
///
/// Anyone can call this to verify a strategy. The verification checks:
/// 1. Minimum 100 signals
/// 2. Minimum 90 days track record
/// 3. Signal frequency >= 2/week average
///
/// If all criteria are met and verification_count reaches 3,
/// is_verified is set to true.

#[derive(Accounts)]
pub struct VerifyTrackRecord<'info> {
    #[account(
        mut,
        seeds = [Performance::SEED, performance.strategy.as_ref()],
        bump = performance.bump,
    )]
    pub performance: Account<'info, Performance>,

    /// The verifier (anyone can verify)
    pub verifier: Signer<'info>,
}

pub fn handler(ctx: Context<VerifyTrackRecord>) -> Result<()> {
    let clock = Clock::get()?;
    let perf = &mut ctx.accounts.performance;

    // Check minimum signals
    require!(
        perf.total_signals >= Performance::MIN_SIGNALS,
        PerformanceError::InsufficientSignals
    );

    // Check minimum track record duration
    let track_record_duration = clock.unix_timestamp
        .saturating_sub(perf.first_signal_at);
    require!(
        track_record_duration >= Performance::MIN_TRACK_RECORD_SECONDS,
        PerformanceError::TrackRecordTooShort
    );

    // Check signal frequency (at least 2 per week on average)
    let weeks = (track_record_duration / (7 * 86_400)).max(1);
    let signals_per_week = perf.total_signals / weeks as u64;
    require!(
        signals_per_week >= 2,
        PerformanceError::SignalFrequencyTooLow
    );

    // Increment verification count
    perf.verification_count = perf.verification_count
        .checked_add(1)
        .ok_or(PerformanceError::ArithmeticOverflow)?;
    perf.last_verified_at = clock.unix_timestamp;

    // Check if verification threshold is met
    if perf.verification_count >= Performance::MIN_VERIFICATIONS && !perf.is_verified {
        perf.is_verified = true;
        msg!(
            "Strategy VERIFIED: {} verifications, {} signals over {} days",
            perf.verification_count,
            perf.total_signals,
            track_record_duration / 86_400,
        );
    } else {
        msg!(
            "Verification recorded: {}/{} needed, verifier={}",
            perf.verification_count,
            Performance::MIN_VERIFICATIONS,
            ctx.accounts.verifier.key(),
        );
    }

    Ok(())
}

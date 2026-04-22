use anchor_lang::prelude::*;
use crate::state::{Performance, RankingPage, RankingEntry};
use crate::errors::PerformanceError;

/// Update ranking for a strategy in a specific category.
/// Permissionless: anyone can trigger ranking updates.
///
/// The ranking score is a composite metric:
/// score = (total_return_bps * 40%) + (win_rate_bps * 30%) - (max_drawdown_bps * 30%)
/// Verified strategies get a 2x bonus.

#[derive(Accounts)]
#[instruction(category: u8, page: u32)]
pub struct UpdateRanking<'info> {
    #[account(
        seeds = [Performance::SEED, performance.strategy.as_ref()],
        bump = performance.bump,
    )]
    pub performance: Account<'info, Performance>,

    #[account(
        init_if_needed,
        payer = caller,
        space = RankingPage::SIZE,
        seeds = [RankingPage::SEED, &[category], page.to_le_bytes().as_ref()],
        bump,
    )]
    pub ranking_page: Account<'info, RankingPage>,

    #[account(mut)]
    pub caller: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<UpdateRanking>, category: u8, page: u32) -> Result<()> {
    let perf = &ctx.accounts.performance;
    let ranking = &mut ctx.accounts.ranking_page;

    // Initialize page if new
    if ranking.category == 0 && ranking.page == 0 && ranking.entry_count == 0 {
        ranking.category = category;
        ranking.page = page;
        ranking.bump = ctx.bumps.ranking_page;
    }

    // Calculate composite score with checked arithmetic
    let return_score = (perf.total_return_bps as i64)
        .checked_mul(40).unwrap_or(0) / 100;
    let win_score = (perf.win_rate_bps as i64)
        .checked_mul(30).unwrap_or(0) / 100;
    let dd_penalty = (perf.max_drawdown_bps as i64)
        .checked_mul(30).unwrap_or(0) / 100;
    let mut score = return_score
        .checked_add(win_score).unwrap_or(i64::MAX)
        .checked_sub(dd_penalty).unwrap_or(i64::MIN);

    // Verified bonus (2x)
    if perf.is_verified {
        score = score.saturating_mul(2);
    }

    let entry = RankingEntry {
        strategy: perf.strategy,
        score,
        total_return_bps: perf.total_return_bps,
        win_rate_bps: perf.win_rate_bps,
        max_drawdown_bps: perf.max_drawdown_bps,
        is_verified: perf.is_verified,
    };

    // Find existing entry or insert
    let mut found = false;
    for i in 0..ranking.entry_count as usize {
        if ranking.entries[i].strategy == perf.strategy {
            ranking.entries[i] = entry;
            found = true;
            break;
        }
    }

    if !found {
        let count = ranking.entry_count as usize;
        if count < 10 {
            ranking.entries[count] = entry;
            ranking.entry_count += 1;
        }
    }

    // Sort entries by score (descending) — simple bubble sort for max 10 entries
    let n = ranking.entry_count as usize;
    for i in 0..n {
        for j in 0..n.saturating_sub(i + 1) {
            if ranking.entries[j].score < ranking.entries[j + 1].score {
                let tmp = ranking.entries[j];
                ranking.entries[j] = ranking.entries[j + 1];
                ranking.entries[j + 1] = tmp;
            }
        }
    }

    let position = {
        let entries = &ranking.entries[..ranking.entry_count as usize];
        entries.iter().position(|e| e.strategy == perf.strategy).unwrap_or(99)
    };

    msg!(
        "Ranking updated: strategy={} score={} category={} position={}",
        perf.strategy,
        score,
        category,
        position,
    );

    Ok(())
}

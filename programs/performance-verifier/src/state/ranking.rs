use anchor_lang::prelude::*;

/// Ranking entry for a strategy in a category.
/// Rankings are stored per category per page (10 entries per page).
#[account]
pub struct RankingPage {
    /// Category (0=overall, 1=paper_only, 2=live_only, 3=btc, 4=eth)
    pub category: u8,
    /// Page number (0-indexed)
    pub page: u32,
    /// Number of entries in this page
    pub entry_count: u8,
    /// Ranking entries (up to 10 per page)
    pub entries: [RankingEntry; 10],
    /// PDA bump
    pub bump: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Default)]
pub struct RankingEntry {
    /// Strategy PDA key
    pub strategy: Pubkey,
    /// Ranking score (higher = better, composite metric)
    pub score: i64,
    /// Total return in basis points
    pub total_return_bps: i32,
    /// Win rate in basis points
    pub win_rate_bps: u16,
    /// Max drawdown in basis points
    pub max_drawdown_bps: u16,
    /// Whether strategy is verified
    pub is_verified: bool,
}

impl RankingPage {
    pub const SEED: &'static [u8] = b"rank";

    pub const SIZE: usize = 8   // discriminator
        + 1                     // category
        + 4                     // page
        + 1                     // entry_count
        + (RankingEntry::SIZE * 10) // entries
        + 1;                    // bump
}

impl RankingEntry {
    pub const SIZE: usize = 32 + 8 + 4 + 2 + 2 + 1; // 49 bytes
}

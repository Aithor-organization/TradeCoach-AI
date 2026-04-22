use anchor_lang::prelude::*;

/// Escrow PDA holds rental funds and distributes them daily.
/// The escrow is a PDA owned by the marketplace program — no human can
/// withdraw funds except through program instructions.
#[account]
pub struct Escrow {
    /// Strategy PDA key
    pub strategy: Pubkey,
    /// Total deposited by renters (lamports)
    pub total_deposited: u64,
    /// Total settled to strategy owner (lamports)
    pub total_settled: u64,
    /// Total refunded to renters on expiry (lamports)
    pub total_refunded: u64,
    /// Daily rental rate (lamports) — cached from strategy
    pub daily_rate: u64,
    /// Last settlement timestamp
    pub last_settled_at: i64,
    /// PDA bump
    pub bump: u8,
}

impl Escrow {
    pub const SEED: &'static [u8] = b"escrow";

    pub const SIZE: usize = 8   // discriminator
        + 32                    // strategy
        + 8                     // total_deposited
        + 8                     // total_settled
        + 8                     // total_refunded
        + 8                     // daily_rate
        + 8                     // last_settled_at
        + 1;                    // bump
}

impl Escrow {
    /// Calculate available balance in escrow
    pub fn available_balance(&self) -> u64 {
        self.total_deposited
            .saturating_sub(self.total_settled)
            .saturating_sub(self.total_refunded)
    }
}

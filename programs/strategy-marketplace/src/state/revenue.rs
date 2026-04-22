use anchor_lang::prelude::*;

#[account]
pub struct Revenue {
    /// Strategy PDA key
    pub strategy: Pubkey,
    /// Strategy owner
    pub authority: Pubkey,
    /// Total earned (lamports)
    pub total_earned: u64,
    /// Total claimed by strategy owner (lamports)
    pub total_claimed: u64,
    /// Pending amount (not yet claimed)
    pub pending_amount: u64,
    /// Platform fee accumulated (lamports)
    pub platform_fee_earned: u64,
    /// Number of permanent purchases
    pub purchase_count: u32,
    /// Number of currently active rentals
    pub active_rentals: u32,
    /// PDA bump
    pub bump: u8,
}

impl Revenue {
    pub const SEED: &'static [u8] = b"revenue";

    pub const SIZE: usize = 8   // discriminator
        + 32                    // strategy
        + 32                    // authority
        + 8                     // total_earned
        + 8                     // total_claimed
        + 8                     // pending_amount
        + 8                     // platform_fee_earned
        + 4                     // purchase_count
        + 4                     // active_rentals
        + 1;                    // bump
}

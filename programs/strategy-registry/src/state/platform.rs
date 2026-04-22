use anchor_lang::prelude::*;

#[account]
pub struct Platform {
    /// Platform administrator
    pub authority: Pubkey,
    /// Total number of strategies registered
    pub strategy_count: u64,
    /// Platform fee in basis points (500 = 5%)
    pub fee_bps: u16,
    /// Treasury wallet for platform fees
    pub treasury: Pubkey,
    /// Emergency pause — when true, all operations are blocked
    pub is_paused: bool,
    /// PDA bump
    pub bump: u8,
}

impl Platform {
    pub const SEED: &'static [u8] = b"platform";

    pub const SIZE: usize = 8  // discriminator
        + 32  // authority
        + 8   // strategy_count
        + 2   // fee_bps
        + 32  // treasury
        + 1   // is_paused
        + 1;  // bump
}

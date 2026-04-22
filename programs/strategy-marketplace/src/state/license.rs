use anchor_lang::prelude::*;

#[account]
pub struct License {
    /// Strategy PDA key
    pub strategy: Pubkey,
    /// Buyer/renter wallet
    pub licensee: Pubkey,
    /// Type of license
    pub license_type: LicenseType,
    /// When the license was created
    pub purchased_at: i64,
    /// Expiration (0 = permanent, >0 = unix timestamp for subscriptions)
    pub expires_at: i64,
    /// Total price paid in lamports
    pub price_paid: u64,
    /// Whether the license is currently active
    pub is_active: bool,
    /// PDA bump
    pub bump: u8,
}

impl License {
    pub const SEED: &'static [u8] = b"license";

    pub const SIZE: usize = 8   // discriminator
        + 32                    // strategy
        + 32                    // licensee
        + 1                     // license_type
        + 8                     // purchased_at
        + 8                     // expires_at
        + 8                     // price_paid
        + 1                     // is_active
        + 1;                    // bump
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq)]
pub enum LicenseType {
    /// One-time permanent purchase
    Permanent,
    /// Time-limited subscription
    Subscription,
}

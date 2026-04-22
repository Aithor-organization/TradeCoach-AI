use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod state;

use instructions::*;

declare_id!("BKmM7ZHuKmg6f5FQbv6rTF44sJkYNR2UsSbvRFGgnmU1");

#[program]
pub mod strategy_marketplace {
    use super::*;

    /// Purchase a strategy permanently.
    /// Atomic: SOL split (95% owner, 5% treasury) + License creation.
    pub fn purchase_strategy(ctx: Context<PurchaseStrategy>) -> Result<()> {
        instructions::purchase::handler(ctx)
    }

    /// Rent a strategy for a specified number of days.
    /// SOL goes to Escrow PDA, released daily via daily_settle.
    pub fn rent_strategy(ctx: Context<RentStrategy>, days: u32) -> Result<()> {
        instructions::rent::handler(ctx, days)
    }

    /// Settle accumulated daily rental fees from escrow to owner.
    /// Permissionless: anyone can crank this.
    pub fn daily_settle(ctx: Context<DailySettle>) -> Result<()> {
        instructions::daily_settle::handler(ctx)
    }

    /// Expire a rental and refund remaining escrow to renter.
    /// Permissionless: anyone can crank this.
    pub fn expire_rental(ctx: Context<ExpireRental>) -> Result<()> {
        instructions::expire_rental::handler(ctx)
    }

    /// Claim accumulated revenue (for tracking/extensions).
    /// Only the strategy owner can call this.
    pub fn claim_revenue(ctx: Context<ClaimRevenue>) -> Result<()> {
        instructions::claim_revenue::handler(ctx)
    }
}

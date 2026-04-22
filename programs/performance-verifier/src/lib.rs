use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod state;

use instructions::*;

declare_id!("J3LeviD4zd9y5izVHLLwgopvEM82A9aUdgXi29wioNCL");

#[program]
pub mod performance_verifier {
    use super::*;

    /// Update performance metrics after a trade closes.
    /// Permissionless: anyone can trigger an update.
    pub fn update_performance(
        ctx: Context<UpdatePerformance>,
        args: UpdatePerformanceArgs,
    ) -> Result<()> {
        instructions::update_performance::handler(ctx, args)
    }

    /// Verify a strategy's track record independently.
    /// Permissionless: anyone can verify. 3+ verifications → is_verified = true.
    pub fn verify_track_record(ctx: Context<VerifyTrackRecord>) -> Result<()> {
        instructions::verify_track_record::handler(ctx)
    }

    /// Update ranking for a strategy in a category.
    /// Permissionless: anyone can trigger ranking updates.
    pub fn update_ranking(ctx: Context<UpdateRanking>, category: u8, page: u32) -> Result<()> {
        instructions::update_ranking::handler(ctx, category, page)
    }
}

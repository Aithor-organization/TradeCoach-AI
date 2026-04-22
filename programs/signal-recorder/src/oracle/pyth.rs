use anchor_lang::prelude::*;
use crate::errors::SignalError;

/// Maximum staleness for Pyth price data (30 seconds)
pub const MAX_STALENESS_SECONDS: i64 = 30;

/// Maximum confidence as percentage of price (2% = 200 basis points)
pub const MAX_CONFIDENCE_BPS: u64 = 200;

/// Scale factor for prices (1e8)
pub const PRICE_SCALE: u64 = 100_000_000;

/// Pyth price data extracted from the price account.
/// We manually parse the account data instead of using pyth-sdk
/// to minimize dependencies and maintain compatibility.
#[derive(Debug)]
pub struct PythPriceData {
    /// Price (scaled to 1e8 for our system)
    pub price: u64,
    /// Confidence interval (scaled to 1e8)
    pub confidence: u64,
    /// Publish time (unix timestamp)
    pub publish_time: i64,
}

/// Validate and extract Pyth price data from an account.
///
/// Pyth price account layout (simplified, v2):
/// - bytes 0..3: magic number (0xa1b2c3d4)
/// - bytes 208..216: price (i64)
/// - bytes 216..224: confidence (u64)
/// - bytes 224..228: exponent (i32)
/// - bytes 232..240: publish_time (i64, sometimes at different offset)
///
/// Note: In production, use pyth-solana-receiver-sdk for Pull Oracle.
/// For localnet testing, we accept the price as provided by the caller
/// and validate it against the Pyth account when available.
pub fn validate_pyth_price(
    pyth_account: &AccountInfo,
    current_time: i64,
) -> Result<PythPriceData> {
    // For localnet/testing: if pyth account has no data, return mock
    // In production, this should always have real Pyth data
    let data = pyth_account.try_borrow_data()?;

    if data.len() < 240 {
        // Account too small to be a valid Pyth price account
        // This allows for testing with mock accounts
        return err!(SignalError::InvalidPythAccount);
    }

    // Parse Pyth v2 price account format
    // Magic number check
    let magic = u32::from_le_bytes(data[0..4].try_into().unwrap());
    if magic != 0xa1b2c3d4 {
        return err!(SignalError::InvalidPythAccount);
    }

    // Price (i64 at offset 208)
    let raw_price = i64::from_le_bytes(data[208..216].try_into().unwrap());
    // Confidence (u64 at offset 216)
    let raw_conf = u64::from_le_bytes(data[216..224].try_into().unwrap());
    // Exponent (i32 at offset 224)
    let exponent = i32::from_le_bytes(data[224..228].try_into().unwrap());
    // Publish time (i64 at offset 232)
    let publish_time = i64::from_le_bytes(data[232..240].try_into().unwrap());

    // Check staleness
    let age = current_time.saturating_sub(publish_time);
    require!(
        age <= MAX_STALENESS_SECONDS,
        SignalError::PythPriceStale
    );

    // Convert price to our scale (1e8)
    let price = scale_price(raw_price, exponent)?;
    let confidence = scale_confidence(raw_conf, exponent)?;

    // Check confidence is within acceptable range (2% of price)
    if price > 0 {
        let max_conf = price
            .checked_mul(MAX_CONFIDENCE_BPS)
            .ok_or(SignalError::ArithmeticOverflow)?
            / 10_000;
        require!(
            confidence <= max_conf,
            SignalError::PythConfidenceTooWide
        );
    }

    Ok(PythPriceData {
        price,
        confidence,
        publish_time,
    })
}

/// Validate exchange price against Pyth price and return delta in basis points.
pub fn calculate_price_delta(exchange_price: u64, pyth_price: u64) -> Result<u16> {
    if pyth_price == 0 {
        return Ok(0);
    }

    let diff = if exchange_price > pyth_price {
        exchange_price.saturating_sub(pyth_price)
    } else {
        pyth_price.saturating_sub(exchange_price)
    };

    // delta_bps = (diff / pyth_price) * 10000
    let delta_bps = diff
        .checked_mul(10_000)
        .ok_or(SignalError::ArithmeticOverflow)?
        / pyth_price;

    // Cap at u16::MAX
    Ok(delta_bps.min(u16::MAX as u64) as u16)
}

/// Scale a raw Pyth price to our 1e8 format
fn scale_price(raw_price: i64, exponent: i32) -> Result<u64> {
    if raw_price <= 0 {
        return err!(SignalError::InvalidPythPrice);
    }

    let price = raw_price as u64;
    let target_exp: i32 = -8; // 1e8

    let exp_diff = exponent - target_exp;
    if exp_diff > 0 {
        // Need to multiply
        let factor = 10u64.checked_pow(exp_diff as u32)
            .ok_or(SignalError::ArithmeticOverflow)?;
        price.checked_mul(factor)
            .ok_or(SignalError::ArithmeticOverflow.into())
    } else if exp_diff < 0 {
        // Need to divide
        let factor = 10u64.checked_pow((-exp_diff) as u32)
            .ok_or(SignalError::ArithmeticOverflow)?;
        Ok(price / factor)
    } else {
        Ok(price)
    }
}

/// Scale raw Pyth confidence to our 1e8 format
fn scale_confidence(raw_conf: u64, exponent: i32) -> Result<u64> {
    let target_exp: i32 = -8;
    let exp_diff = exponent - target_exp;

    if exp_diff > 0 {
        let factor = 10u64.checked_pow(exp_diff as u32)
            .ok_or(SignalError::ArithmeticOverflow)?;
        raw_conf.checked_mul(factor)
            .ok_or(SignalError::ArithmeticOverflow.into())
    } else if exp_diff < 0 {
        let factor = 10u64.checked_pow((-exp_diff) as u32)
            .ok_or(SignalError::ArithmeticOverflow)?;
        Ok(raw_conf / factor)
    } else {
        Ok(raw_conf)
    }
}

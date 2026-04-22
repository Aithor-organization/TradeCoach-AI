CREATE TABLE IF NOT EXISTS strategy_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL, creator_address VARCHAR(44) NOT NULL,
    listing_type VARCHAR(10) DEFAULT 'both', price_usdc NUMERIC(20,6),
    rental_price_per_day NUMERIC(20,6), status VARCHAR(20) DEFAULT 'active',
    is_verified BOOLEAN DEFAULT FALSE, total_purchases INT DEFAULT 0,
    total_rentals INT DEFAULT 0, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES strategy_listings(id),
    strategy_id UUID NOT NULL, holder_address VARCHAR(44) NOT NULL,
    license_type VARCHAR(20) NOT NULL, status VARCHAR(20) DEFAULT 'active',
    expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS rental_escrow (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES strategy_listings(id),
    renter_address VARCHAR(44) NOT NULL, creator_address VARCHAR(44) NOT NULL,
    rental_days INT NOT NULL, daily_rate_usdc NUMERIC(20,6) NOT NULL,
    total_amount_usdc NUMERIC(20,6) NOT NULL, settled_days INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', start_date TIMESTAMPTZ, end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS purchase_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID REFERENCES strategy_listings(id),
    buyer_address VARCHAR(44) NOT NULL, creator_address VARCHAR(44) NOT NULL,
    price_usdc NUMERIC(20,6) NOT NULL, creator_amount_usdc NUMERIC(20,6) NOT NULL,
    platform_amount_usdc NUMERIC(20,6) NOT NULL, transaction_hash VARCHAR(88),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS revenue_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID, creator_address VARCHAR(44) NOT NULL,
    amount_usdc NUMERIC(20,6) NOT NULL, revenue_type VARCHAR(30) NOT NULL,
    claimed BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS strategy_rankings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL, category VARCHAR(20) DEFAULT 'overall',
    score NUMERIC(15,6) DEFAULT 0, rank INT, is_verified BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT now(), UNIQUE(strategy_id, category)
);

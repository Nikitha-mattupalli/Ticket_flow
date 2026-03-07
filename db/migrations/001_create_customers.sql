-- ============================================================
-- Migration: 001_create_customers
-- Description: Create customers table with tier support
-- Created: 2025-03-07
-- ============================================================

-- UP ↑ (apply)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS customers (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT        NOT NULL,
    email        TEXT        NOT NULL UNIQUE,
    phone        TEXT,
    tier         TEXT        NOT NULL DEFAULT 'standard'
                             CHECK (tier IN ('standard', 'premium', 'enterprise')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  customers      IS 'End users who raise tickets or place orders';
COMMENT ON COLUMN customers.tier IS 'Customer tier affects SLA priority';

-- auto-update trigger function (shared across all tables)
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- DOWN ↓ (rollback)
-- ------------------------------------------------------------
-- DROP TRIGGER IF EXISTS trg_customers_updated_at ON customers;
-- DROP TABLE IF EXISTS customers;
-- DROP FUNCTION IF EXISTS update_updated_at();
-- ============================================================
-- Migration: 002_create_orders
-- Description: Create orders table linked to customers
-- Depends on: 001_create_customers
-- Created: 2025-03-07
-- ============================================================

-- UP ↑ (apply)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS orders (
    id             UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id    UUID           NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_number   TEXT           NOT NULL UNIQUE,
    status         TEXT           NOT NULL DEFAULT 'pending'
                                  CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled', 'refunded')),
    total_amount   NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    currency       TEXT           NOT NULL DEFAULT 'INR',
    notes          TEXT,
    placed_at      TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ    NOT NULL DEFAULT now()
);

COMMENT ON TABLE  orders              IS 'Customer purchases or subscriptions';
COMMENT ON COLUMN orders.order_number IS 'Human-readable order reference e.g. ORD-2025-001';
COMMENT ON COLUMN orders.status       IS 'Order lifecycle: pending → confirmed → shipped → delivered';

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status       ON orders(status);


-- DOWN ↓ (rollback)
-- ------------------------------------------------------------
-- DROP TRIGGER IF EXISTS trg_orders_updated_at ON orders;
-- DROP INDEX  IF EXISTS idx_orders_customer_id;
-- DROP INDEX  IF EXISTS idx_orders_status;
-- DROP TABLE  IF EXISTS orders;
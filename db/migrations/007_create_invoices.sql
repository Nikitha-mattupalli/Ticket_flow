-- ============================================================
-- Migration: 007_create_invoices
-- Description: Invoices tied to customers and optionally orders
-- Depends on: 001_create_customers, 002_create_orders
-- Created: 2025-03-07
-- ============================================================

-- UP ↑ (apply)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS invoices (
    id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID           NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_id        UUID           REFERENCES orders(id) ON DELETE SET NULL,

    invoice_number  TEXT           NOT NULL UNIQUE,   -- e.g. INV-2025-001
    status          TEXT           NOT NULL DEFAULT 'unpaid'
                                   CHECK (status IN ('draft', 'unpaid', 'paid', 'overdue', 'void')),

    subtotal        NUMERIC(10, 2) NOT NULL CHECK (subtotal >= 0),
    tax_rate        NUMERIC(5, 2)  NOT NULL DEFAULT 0.18,   -- 18% GST default
    tax_amount      NUMERIC(10, 2) GENERATED ALWAYS AS (ROUND(subtotal * tax_rate, 2)) STORED,
    total_amount    NUMERIC(10, 2) GENERATED ALWAYS AS (ROUND(subtotal + subtotal * tax_rate, 2)) STORED,

    currency        TEXT           NOT NULL DEFAULT 'INR',
    description     TEXT,

    issued_at       TIMESTAMPTZ    NOT NULL DEFAULT now(),
    due_at          TIMESTAMPTZ    NOT NULL DEFAULT (now() + INTERVAL '30 days'),
    paid_at         TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ    NOT NULL DEFAULT now()
);

COMMENT ON TABLE  invoices                IS 'Invoices issued to customers, optionally linked to an order';
COMMENT ON COLUMN invoices.tax_amount     IS 'Auto-computed: subtotal * tax_rate';
COMMENT ON COLUMN invoices.total_amount   IS 'Auto-computed: subtotal + tax_amount';
COMMENT ON COLUMN invoices.due_at         IS 'Payment due date — default 30 days from issue';

CREATE TRIGGER trg_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_invoices_customer_id    ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_order_id       ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status         ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due_at         ON invoices(due_at);


-- DOWN ↓ (rollback)
-- ------------------------------------------------------------
-- DROP TRIGGER IF EXISTS trg_invoices_updated_at ON invoices;
-- DROP INDEX  IF EXISTS idx_invoices_customer_id;
-- DROP INDEX  IF EXISTS idx_invoices_order_id;
-- DROP INDEX  IF EXISTS idx_invoices_status;
-- DROP INDEX  IF EXISTS idx_invoices_due_at;
-- DROP TABLE  IF EXISTS invoices;
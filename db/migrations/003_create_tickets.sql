-- ============================================================
-- Migration: 003_create_tickets
-- Description: Create tickets table linked to customers + orders
-- Depends on: 001_create_customers, 002_create_orders
-- Created: 2025-03-07
-- ============================================================

-- UP ↑ (apply)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tickets (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id   UUID        NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_id      UUID        REFERENCES orders(id) ON DELETE SET NULL,  -- nullable

    ticket_number TEXT        NOT NULL UNIQUE,
    title         TEXT        NOT NULL,
    description   TEXT,

    category      TEXT        NOT NULL DEFAULT 'general'
                              CHECK (category IN ('billing', 'tech', 'policy', 'escalation', 'general')),
    status        TEXT        NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open', 'in_progress', 'waiting', 'resolved', 'closed')),
    priority      TEXT        NOT NULL DEFAULT 'medium'
                              CHECK (priority IN ('low', 'medium', 'high', 'urgent')),

    assigned_to   TEXT,
    resolved_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  tickets            IS 'Support tickets raised by customers';
COMMENT ON COLUMN tickets.order_id   IS 'Nullable — only set when ticket relates to a specific order';
COMMENT ON COLUMN tickets.category   IS 'Maps to Ticketflow supervisor routing: billing/tech/policy/escalation';
COMMENT ON COLUMN tickets.priority   IS 'Drives SLA: urgent=4hr, high=8hr, medium=24hr, low=72hr';

CREATE TRIGGER trg_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_order_id    ON tickets(order_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status      ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_category    ON tickets(category);
CREATE INDEX IF NOT EXISTS idx_tickets_priority    ON tickets(priority);


-- DOWN ↓ (rollback)
-- ------------------------------------------------------------
-- DROP TRIGGER IF EXISTS trg_tickets_updated_at ON tickets;
-- DROP INDEX  IF EXISTS idx_tickets_customer_id;
-- DROP INDEX  IF EXISTS idx_tickets_order_id;
-- DROP INDEX  IF EXISTS idx_tickets_status;
-- DROP INDEX  IF EXISTS idx_tickets_category;
-- DROP INDEX  IF EXISTS idx_tickets_priority;
-- DROP TABLE  IF EXISTS tickets;
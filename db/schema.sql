-- ============================================================
-- Ticketflow DB Schema
-- Tables: customers, orders, tickets
-- Run this in Supabase SQL Editor (supabase.com → SQL Editor)
-- ============================================================


-- ─────────────────────────────────────────────
-- 1. CUSTOMERS
-- Who raised the ticket / placed the order
-- ─────────────────────────────────────────────

CREATE TABLE customers (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT        NOT NULL,
    email        TEXT        NOT NULL UNIQUE,
    phone        TEXT,
    tier         TEXT        NOT NULL DEFAULT 'standard'
                             CHECK (tier IN ('standard', 'premium', 'enterprise')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  customers       IS 'End users who raise tickets or place orders';
COMMENT ON COLUMN customers.tier  IS 'Customer tier affects SLA priority';


-- ─────────────────────────────────────────────
-- 2. ORDERS
-- Purchase / subscription linked to a customer
-- ─────────────────────────────────────────────

CREATE TABLE orders (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id    UUID        NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_number   TEXT        NOT NULL UNIQUE,   -- e.g. ORD-2025-001
    status         TEXT        NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled', 'refunded')),
    total_amount   NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    currency       TEXT        NOT NULL DEFAULT 'INR',
    notes          TEXT,
    placed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  orders              IS 'Customer purchases or subscriptions';
COMMENT ON COLUMN orders.order_number IS 'Human-readable order reference';


-- ─────────────────────────────────────────────
-- 3. TICKETS
-- Support tickets — linked to customer, optionally to an order
-- ─────────────────────────────────────────────

CREATE TABLE tickets (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id   UUID        NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_id      UUID        REFERENCES orders(id) ON DELETE SET NULL,  -- optional

    ticket_number TEXT        NOT NULL UNIQUE,    -- e.g. TKT-2025-001
    title         TEXT        NOT NULL,
    description   TEXT,

    category      TEXT        NOT NULL DEFAULT 'general'
                              CHECK (category IN ('billing', 'tech', 'policy', 'escalation', 'general')),
    status        TEXT        NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open', 'in_progress', 'waiting', 'resolved', 'closed')),
    priority      TEXT        NOT NULL DEFAULT 'medium'
                              CHECK (priority IN ('low', 'medium', 'high', 'urgent')),

    assigned_to   TEXT,       -- agent name or ID
    resolved_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  tickets           IS 'Support tickets raised by customers';
COMMENT ON COLUMN tickets.order_id  IS 'Optional — set when ticket is about a specific order';
COMMENT ON COLUMN tickets.category  IS 'Maps to Ticketflow agent routing: billing/tech/policy/escalation';


-- ─────────────────────────────────────────────
-- 4. AUTO-UPDATE updated_at on row change
-- ─────────────────────────────────────────────

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

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ─────────────────────────────────────────────
-- 5. INDEXES for common query patterns
-- ─────────────────────────────────────────────

CREATE INDEX idx_tickets_customer_id  ON tickets(customer_id);
CREATE INDEX idx_tickets_order_id     ON tickets(order_id);
CREATE INDEX idx_tickets_status       ON tickets(status);
CREATE INDEX idx_tickets_category     ON tickets(category);
CREATE INDEX idx_tickets_priority     ON tickets(priority);
CREATE INDEX idx_orders_customer_id   ON orders(customer_id);
CREATE INDEX idx_orders_status        ON orders(status);


-- ─────────────────────────────────────────────
-- 6. SEED DATA — sample rows to test with
-- ─────────────────────────────────────────────

INSERT INTO customers (name, email, phone, tier) VALUES
    ('Alice Sharma',   'alice@example.com',   '+91-9876543210', 'enterprise'),
    ('Bob Mehta',      'bob@example.com',     '+91-9123456789', 'premium'),
    ('Charlie Nair',   'charlie@example.com', '+91-9988776655', 'standard'),
    ('Diana Iyer',     'diana@example.com',   '+91-9001122334', 'premium');

INSERT INTO orders (customer_id, order_number, status, total_amount, currency) VALUES
    ((SELECT id FROM customers WHERE email = 'alice@example.com'),   'ORD-2025-001', 'delivered',  12999.00, 'INR'),
    ((SELECT id FROM customers WHERE email = 'bob@example.com'),     'ORD-2025-002', 'shipped',     4599.00, 'INR'),
    ((SELECT id FROM customers WHERE email = 'charlie@example.com'), 'ORD-2025-003', 'pending',     1999.00, 'INR'),
    ((SELECT id FROM customers WHERE email = 'diana@example.com'),   'ORD-2025-004', 'cancelled',   8499.00, 'INR');

INSERT INTO tickets (customer_id, order_id, ticket_number, title, description, category, status, priority) VALUES
    (
        (SELECT id FROM customers WHERE email = 'alice@example.com'),
        (SELECT id FROM orders WHERE order_number = 'ORD-2025-001'),
        'TKT-2025-001', 'Invoice shows wrong amount',
        'My invoice for ORD-2025-001 shows 14999 but I was charged 12999.',
        'billing', 'open', 'high'
    ),
    (
        (SELECT id FROM customers WHERE email = 'bob@example.com'),
        (SELECT id FROM orders WHERE order_number = 'ORD-2025-002'),
        'TKT-2025-002', 'Integration API returning 500',
        'The webhook endpoint keeps returning 500 errors since yesterday.',
        'tech', 'in_progress', 'urgent'
    ),
    (
        (SELECT id FROM customers WHERE email = 'charlie@example.com'),
        NULL,
        'TKT-2025-003', 'Question about refund policy',
        'What is the return window for software products?',
        'policy', 'open', 'low'
    ),
    (
        (SELECT id FROM customers WHERE email = 'diana@example.com'),
        (SELECT id FROM orders WHERE order_number = 'ORD-2025-004'),
        'TKT-2025-004', 'Cancelled order not refunded after 7 days',
        'Order was cancelled on March 1st. Refund still not received.',
        'escalation', 'open', 'urgent'
    );


-- ─────────────────────────────────────────────
-- 7. VERIFY — run these to check everything
-- ─────────────────────────────────────────────

SELECT 'customers' AS tbl, count(*) FROM customers
UNION ALL
SELECT 'orders',   count(*) FROM orders
UNION ALL
SELECT 'tickets',  count(*) FROM tickets;

-- Full join: ticket + customer + order
SELECT
    t.ticket_number,
    t.title,
    t.category,
    t.status,
    t.priority,
    c.name        AS customer,
    c.tier,
    o.order_number
FROM tickets t
JOIN customers c ON c.id = t.customer_id
LEFT JOIN orders o ON o.id = t.order_id
ORDER BY t.created_at;
-- ============================================================
-- Migration: 006_seed_data
-- Description: Insert sample customers, orders, tickets, notes
-- Depends on: 001 → 005
-- Created: 2025-03-07
-- ============================================================

-- UP ↑ (apply)
-- ------------------------------------------------------------

INSERT INTO customers (name, email, phone, tier) VALUES
    ('Alice Sharma',  'alice@example.com',   '+91-9876543210', 'enterprise'),
    ('Bob Mehta',     'bob@example.com',     '+91-9123456789', 'premium'),
    ('Charlie Nair',  'charlie@example.com', '+91-9988776655', 'standard'),
    ('Diana Iyer',    'diana@example.com',   '+91-9001122334', 'premium')
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (customer_id, order_number, status, total_amount, currency) VALUES
    ((SELECT id FROM customers WHERE email = 'alice@example.com'),   'ORD-2025-001', 'delivered', 12999.00, 'INR'),
    ((SELECT id FROM customers WHERE email = 'bob@example.com'),     'ORD-2025-002', 'shipped',    4599.00, 'INR'),
    ((SELECT id FROM customers WHERE email = 'charlie@example.com'), 'ORD-2025-003', 'pending',    1999.00, 'INR'),
    ((SELECT id FROM customers WHERE email = 'diana@example.com'),   'ORD-2025-004', 'cancelled',  8499.00, 'INR')
ON CONFLICT (order_number) DO NOTHING;

INSERT INTO tickets (customer_id, order_id, ticket_number, title, description, category, status, priority, tags) VALUES
    (
        (SELECT id FROM customers WHERE email = 'alice@example.com'),
        (SELECT id FROM orders   WHERE order_number = 'ORD-2025-001'),
        'TKT-2025-001',
        'Invoice shows wrong amount',
        'Invoice for ORD-2025-001 shows 14999 but I was charged 12999.',
        'billing', 'open', 'high',
        ARRAY['invoice', 'overcharge']
    ),
    (
        (SELECT id FROM customers WHERE email = 'bob@example.com'),
        (SELECT id FROM orders   WHERE order_number = 'ORD-2025-002'),
        'TKT-2025-002',
        'Integration API returning 500',
        'Webhook endpoint keeps returning 500 errors since yesterday.',
        'tech', 'in_progress', 'urgent',
        ARRAY['api', 'outage', 'webhook']
    ),
    (
        (SELECT id FROM customers WHERE email = 'charlie@example.com'),
        NULL,
        'TKT-2025-003',
        'Question about refund policy',
        'What is the return window for software products?',
        'policy', 'open', 'low',
        ARRAY['refund', 'policy']
    ),
    (
        (SELECT id FROM customers WHERE email = 'diana@example.com'),
        (SELECT id FROM orders   WHERE order_number = 'ORD-2025-004'),
        'TKT-2025-004',
        'Cancelled order not refunded after 7 days',
        'Order cancelled on March 1st. Refund still not received.',
        'escalation', 'open', 'urgent',
        ARRAY['refund', 'vip', 'escalation']
    )
ON CONFLICT (ticket_number) DO NOTHING;

INSERT INTO ticket_notes (ticket_id, author, body, is_internal) VALUES
    (
        (SELECT id FROM tickets WHERE ticket_number = 'TKT-2025-001'),
        'system', 'Ticket auto-routed to billing agent.', true
    ),
    (
        (SELECT id FROM tickets WHERE ticket_number = 'TKT-2025-002'),
        'system', 'Ticket auto-routed to tech support agent.', true
    ),
    (
        (SELECT id FROM tickets WHERE ticket_number = 'TKT-2025-002'),
        'agent-bob', 'Investigated webhook logs — found timeout issue. Fix deploying in 2hrs.', true
    ),
    (
        (SELECT id FROM tickets WHERE ticket_number = 'TKT-2025-004'),
        'system', 'Ticket escalated — SLA breach imminent. Paging human agent.', true
    );


-- DOWN ↓ (rollback)
-- ------------------------------------------------------------
-- DELETE FROM ticket_notes;
-- DELETE FROM tickets;
-- DELETE FROM orders;
-- DELETE FROM customers;


-- VERIFY
-- ------------------------------------------------------------
SELECT 'customers'    AS tbl, count(*) FROM customers
UNION ALL
SELECT 'orders',               count(*) FROM orders
UNION ALL
SELECT 'tickets',              count(*) FROM tickets
UNION ALL
SELECT 'ticket_notes',         count(*) FROM ticket_notes;
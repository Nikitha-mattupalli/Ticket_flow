-- ============================================================
-- Migration: 005_create_ticket_notes
-- Description: Audit trail / internal notes per ticket
-- Depends on: 003_create_tickets
-- Created: 2025-03-07
-- ============================================================

-- UP ↑ (apply)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ticket_notes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id   UUID        NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    author      TEXT        NOT NULL,           -- agent name or "system"
    body        TEXT        NOT NULL,
    is_internal BOOLEAN     NOT NULL DEFAULT true,  -- false = visible to customer
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  ticket_notes             IS 'Internal notes and audit trail for each ticket';
COMMENT ON COLUMN ticket_notes.is_internal IS 'true = agent-only note, false = customer-visible reply';

CREATE INDEX IF NOT EXISTS idx_ticket_notes_ticket_id ON ticket_notes(ticket_id);


-- DOWN ↓ (rollback)
-- ------------------------------------------------------------
-- DROP INDEX IF EXISTS idx_ticket_notes_ticket_id;
-- DROP TABLE IF EXISTS ticket_notes;
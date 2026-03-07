-- ============================================================
-- Migration: 004_add_sla_and_tags_to_tickets
-- Description: Add sla_due_at deadline + tags array to tickets
-- Depends on: 003_create_tickets
-- Created: 2025-03-07
-- ============================================================

-- UP ↑ (apply)
-- ------------------------------------------------------------

-- SLA deadline — computed from priority at insert time
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMPTZ;

-- Free-form tags array e.g. ARRAY['refund', 'vip', 'follow-up']
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

COMMENT ON COLUMN tickets.sla_due_at IS 'SLA deadline: urgent=+4h, high=+8h, medium=+24h, low=+72h';
COMMENT ON COLUMN tickets.tags       IS 'Free-form labels for filtering and search';

-- Auto-populate sla_due_at on INSERT based on priority
CREATE OR REPLACE FUNCTION set_sla_due_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.sla_due_at := CASE NEW.priority
        WHEN 'urgent' THEN now() + INTERVAL  '4 hours'
        WHEN 'high'   THEN now() + INTERVAL  '8 hours'
        WHEN 'medium' THEN now() + INTERVAL '24 hours'
        WHEN 'low'    THEN now() + INTERVAL '72 hours'
        ELSE now() + INTERVAL '24 hours'
    END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tickets_sla_due_at
    BEFORE INSERT ON tickets
    FOR EACH ROW EXECUTE FUNCTION set_sla_due_at();

-- Index for SLA breach queries ("show all tickets past due")
CREATE INDEX IF NOT EXISTS idx_tickets_sla_due_at ON tickets(sla_due_at);

-- GIN index for fast tag array lookups e.g. WHERE 'vip' = ANY(tags)
CREATE INDEX IF NOT EXISTS idx_tickets_tags ON tickets USING GIN(tags);


-- DOWN ↓ (rollback)
-- ------------------------------------------------------------
-- DROP TRIGGER IF EXISTS trg_tickets_sla_due_at ON tickets;
-- DROP FUNCTION IF EXISTS set_sla_due_at();
-- DROP INDEX IF EXISTS idx_tickets_sla_due_at;
-- DROP INDEX IF EXISTS idx_tickets_tags;
-- ALTER TABLE tickets DROP COLUMN IF EXISTS sla_due_at;
-- ALTER TABLE tickets DROP COLUMN IF EXISTS tags;
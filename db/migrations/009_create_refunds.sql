-- ============================================================
-- Migration: 009_create_refunds
-- Description: Refund requests and Stripe refund outcomes
-- Depends on: 008_create_payments
-- ============================================================

-- UP ↑
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS refunds (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    payment_id          UUID NOT NULL,
    invoice_id          UUID NOT NULL,
    customer_id         UUID NOT NULL,

    stripe_refund_id    TEXT UNIQUE,

    amount              NUMERIC(10, 2) NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'INR',

    reason              TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',

    approval_required   BOOLEAN NOT NULL DEFAULT false,
    approved_by         TEXT,
    approved_at         TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT refunds_payment_id_fkey
        FOREIGN KEY (payment_id)
        REFERENCES payments(id)
        ON DELETE RESTRICT,

    CONSTRAINT refunds_invoice_id_fkey
        FOREIGN KEY (invoice_id)
        REFERENCES invoices(id)
        ON DELETE RESTRICT,

    CONSTRAINT refunds_customer_id_fkey
        FOREIGN KEY (customer_id)
        REFERENCES customers(id)
        ON DELETE RESTRICT,

    CONSTRAINT refunds_amount_check
        CHECK (amount > 0),

    CONSTRAINT refunds_reason_check
        CHECK (
            reason IN (
                'duplicate',
                'fraudulent',
                'requested_by_customer',
                'billing_error',
                'service_issue'
            )
        ),

    CONSTRAINT refunds_status_check
        CHECK (
            status IN (
                'pending',
                'approval_required',
                'processing',
                'succeeded',
                'failed',
                'cancelled'
            )
        )
);

COMMENT ON TABLE refunds IS
    'Refund requests, approval state, and Stripe refund outcomes';

COMMENT ON COLUMN refunds.stripe_refund_id IS
    'Stripe Refund identifier, normally beginning with re_';

CREATE INDEX IF NOT EXISTS idx_refunds_payment_id
    ON refunds(payment_id);

CREATE INDEX IF NOT EXISTS idx_refunds_invoice_id
    ON refunds(invoice_id);

CREATE INDEX IF NOT EXISTS idx_refunds_customer_id
    ON refunds(customer_id);

CREATE INDEX IF NOT EXISTS idx_refunds_status
    ON refunds(status);

CREATE INDEX IF NOT EXISTS idx_refunds_approval_required
    ON refunds(approval_required);

CREATE TRIGGER trg_refunds_updated_at
    BEFORE UPDATE ON refunds
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();


-- DOWN ↓
-- ------------------------------------------------------------
-- DROP TRIGGER IF EXISTS trg_refunds_updated_at ON refunds;
-- DROP INDEX IF EXISTS idx_refunds_approval_required;
-- DROP INDEX IF EXISTS idx_refunds_status;
-- DROP INDEX IF EXISTS idx_refunds_customer_id;
-- DROP INDEX IF EXISTS idx_refunds_invoice_id;
-- DROP INDEX IF EXISTS idx_refunds_payment_id;
-- DROP TABLE IF EXISTS refunds;
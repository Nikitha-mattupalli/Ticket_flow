-- ============================================================
-- Migration: 008_create_payments
-- Description: Stripe payment transactions linked to invoices
-- Depends on: 001_create_customers, 007_create_invoices
-- ============================================================

-- UP ↑
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS payments (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    invoice_id               UUID NOT NULL,
    customer_id              UUID NOT NULL,

    stripe_payment_intent_id TEXT UNIQUE,
    stripe_charge_id         TEXT UNIQUE,

    status                   TEXT NOT NULL DEFAULT 'pending',

    amount                   NUMERIC(10, 2) NOT NULL,
    currency                 TEXT NOT NULL DEFAULT 'INR',

    payment_method           TEXT,

    paid_at                  TIMESTAMPTZ,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT payments_invoice_id_fkey
        FOREIGN KEY (invoice_id)
        REFERENCES invoices(id)
        ON DELETE CASCADE,

    CONSTRAINT payments_customer_id_fkey
        FOREIGN KEY (customer_id)
        REFERENCES customers(id)
        ON DELETE CASCADE,

    CONSTRAINT payments_status_check
        CHECK (
            status IN (
                'pending',
                'processing',
                'succeeded',
                'failed',
                'refunded',
                'partially_refunded'
            )
        ),

    CONSTRAINT payments_amount_check
        CHECK (amount > 0)
);

COMMENT ON TABLE payments IS
    'Payment attempts and successful transactions associated with invoices';

COMMENT ON COLUMN payments.stripe_payment_intent_id IS
    'Stripe PaymentIntent identifier, normally beginning with pi_';

COMMENT ON COLUMN payments.stripe_charge_id IS
    'Stripe Charge identifier, normally beginning with ch_';

CREATE INDEX IF NOT EXISTS idx_payments_invoice_id
    ON payments(invoice_id);

CREATE INDEX IF NOT EXISTS idx_payments_customer_id
    ON payments(customer_id);

CREATE INDEX IF NOT EXISTS idx_payments_status
    ON payments(status);

CREATE INDEX IF NOT EXISTS idx_payments_payment_intent
    ON payments(stripe_payment_intent_id);

CREATE TRIGGER trg_payments_updated_at
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();


-- DOWN ↓
-- ------------------------------------------------------------
-- DROP TRIGGER IF EXISTS trg_payments_updated_at ON payments;
-- DROP INDEX IF EXISTS idx_payments_payment_intent;
-- DROP INDEX IF EXISTS idx_payments_status;
-- DROP INDEX IF EXISTS idx_payments_customer_id;
-- DROP INDEX IF EXISTS idx_payments_invoice_id;
-- DROP TABLE IF EXISTS payments;
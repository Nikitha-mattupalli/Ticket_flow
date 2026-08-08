-- Store provider-facing refund amounts without floating-point conversion.
ALTER TABLE refunds
    ADD COLUMN IF NOT EXISTS amount_minor BIGINT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'refunds_amount_minor_check'
    ) THEN
        ALTER TABLE refunds
            ADD CONSTRAINT refunds_amount_minor_check
            CHECK (amount_minor IS NULL OR amount_minor > 0);
    END IF;
END $$;

COMMENT ON COLUMN refunds.amount_minor IS
    'Refund amount in the smallest currency unit (cents, paise, etc.).';

-- Existing `amount` remains for backward compatibility with seeded rows.

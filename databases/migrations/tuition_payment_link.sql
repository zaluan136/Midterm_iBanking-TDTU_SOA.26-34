-- Run against tuition_database.
ALTER TABLE tuition_fee
    ADD COLUMN IF NOT EXISTS payment_transaction_code VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tuition_payment_transaction
    ON tuition_fee(payment_transaction_code)
    WHERE payment_transaction_code IS NOT NULL;

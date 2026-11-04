-- Run against payment_database.
ALTER TABLE payment_transaction
    ADD COLUMN IF NOT EXISTS email_sent BOOLEAN NOT NULL DEFAULT FALSE;

-- Run against otp_database. Existing one-time codes are converted on first use
-- by new challenges; old records remain invalid once expired.
ALTER TABLE otp
    ALTER COLUMN otp_code TYPE VARCHAR(64),
    ADD COLUMN IF NOT EXISTS attempt_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS verified BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_otp_one_active_per_txn
    ON otp(transaction_id) WHERE used = FALSE;

-- Run against otp_database.
CREATE TABLE IF NOT EXISTS email_delivery (
    transaction_code VARCHAR(64) PRIMARY KEY,
    recipient VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'sent')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMPTZ
);

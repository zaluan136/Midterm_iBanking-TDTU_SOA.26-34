-- OTP Service owns this DB
CREATE TABLE otp (
    id SERIAL PRIMARY KEY,
    otp_code VARCHAR(64) NOT NULL, -- HMAC-SHA-256 hash; never store the plaintext code
    transaction_id INT NOT NULL,       -- logical ref tới payment_transaction.id
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    attempt_count INT NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_otp_txn ON otp(transaction_id);
CREATE UNIQUE INDEX idx_otp_one_active_per_txn 
    ON otp(transaction_id) WHERE used = false;

CREATE TABLE email_delivery (
    transaction_code VARCHAR(64) PRIMARY KEY,
    recipient VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'sent')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMPTZ
);

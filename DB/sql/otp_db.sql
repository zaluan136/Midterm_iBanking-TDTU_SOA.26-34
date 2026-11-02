-- OTP Service owns this DB
CREATE TABLE otp (
    id SERIAL PRIMARY KEY,
    otp_code VARCHAR(10) NOT NULL,
    transaction_id INT NOT NULL,       -- logical ref tới payment_transaction.id
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_otp_txn ON otp(transaction_id);
CREATE UNIQUE INDEX idx_otp_one_active_per_txn 
    ON otp(transaction_id) WHERE used = false;
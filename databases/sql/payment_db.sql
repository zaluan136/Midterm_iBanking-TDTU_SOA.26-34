-- Payment Service owns this DB
-- LƯU Ý: KHÔNG có FK constraint (khác DB)
CREATE TABLE payment_transaction (
    id SERIAL PRIMARY KEY,
    transaction_code VARCHAR(64) UNIQUE NOT NULL,
    payer_user_id INT NOT NULL,        -- logical ref tới app_user.id
    tuition_fee_id INT NOT NULL,       -- logical ref tới tuition_fee.id
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    status VARCHAR(30) DEFAULT 'pending_otp' 
        CHECK (status IN ('pending_otp', 'processing', 'success', 'failed', 'expired', 'refunded')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    email_sent BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_txn_payer ON payment_transaction(payer_user_id, created_at DESC);
CREATE INDEX idx_txn_status ON payment_transaction(status);

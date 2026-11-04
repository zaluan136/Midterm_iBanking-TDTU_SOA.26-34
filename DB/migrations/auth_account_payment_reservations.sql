-- Run against auth_database.
CREATE TABLE IF NOT EXISTS account_reservation (
    transaction_code VARCHAR(64) PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(id),
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('reserved', 'committed', 'released')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

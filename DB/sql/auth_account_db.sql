-- Auth-Account Service owns this DB
CREATE TABLE app_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100) NOT NULL,
    balance DECIMAL(15, 2) DEFAULT 0.00 CHECK (balance >= 0),
    version INT DEFAULT 0
);

CREATE INDEX idx_user_username ON app_user(username);

CREATE TABLE account_reservation (
    transaction_code VARCHAR(64) PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(id),
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('reserved', 'committed', 'released')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

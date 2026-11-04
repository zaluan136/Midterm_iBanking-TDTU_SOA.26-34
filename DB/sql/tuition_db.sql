-- Tuition Service owns this DB
CREATE TABLE tuition_fee (
    id SERIAL PRIMARY KEY,
    mssv VARCHAR(20) NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    semester VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'unpaid' CHECK (status IN ('unpaid', 'paid')),
    version INT DEFAULT 0,
    payment_transaction_code VARCHAR(64) UNIQUE
);

CREATE INDEX idx_tuition_mssv ON tuition_fee(mssv);
CREATE INDEX idx_tuition_status ON tuition_fee(status);

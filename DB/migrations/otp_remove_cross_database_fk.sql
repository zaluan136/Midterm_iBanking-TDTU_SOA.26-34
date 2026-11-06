-- Run against otp_database only.
-- payment_transaction belongs to payment_database, not otp_database.
-- OTP Service stores transaction_id as a logical reference.
ALTER TABLE otp
    DROP CONSTRAINT IF EXISTS otp_transaction_id_fkey;

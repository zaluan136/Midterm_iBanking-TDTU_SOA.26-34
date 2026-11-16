-- Run against payment_database only.
-- User and tuition records belong to other service databases, so these
-- references must be checked by their owning services over HTTP.
ALTER TABLE payment_transaction
    DROP CONSTRAINT IF EXISTS payment_transaction_payer_user_id_fkey,
    DROP CONSTRAINT IF EXISTS payment_transaction_tuition_fee_id_fkey;

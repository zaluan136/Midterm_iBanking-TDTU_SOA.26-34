"""Add retry-safe payment bookkeeping; run once before starting services."""
from services.common import database

if __name__ == '__main__':
    with database('auth_database') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS account_payment (
            transaction_code TEXT PRIMARY KEY, user_id INT NOT NULL REFERENCES app_user(id),
            amount NUMERIC(15,2) NOT NULL CHECK(amount > 0), refunded BOOLEAN NOT NULL DEFAULT FALSE)''')
    with database('tuition_database') as conn:
        conn.execute('ALTER TABLE tuition_fee ADD COLUMN IF NOT EXISTS paid_by_transaction TEXT UNIQUE')
    print('Đã chuẩn bị database cho thanh toán thử.')

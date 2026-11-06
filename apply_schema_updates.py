"""Apply the existing iBanking migrations to their matching Neon databases."""
from pathlib import Path

from services.common import database


ROOT = Path(__file__).resolve().parent / 'DB' / 'migrations'
MIGRATIONS = {
    'auth_database': ['auth_account_payment_reservations.sql'],
    'tuition_database': ['tuition_payment_link.sql'],
    'payment_database': ['payment_email_status.sql', 'payment_remove_cross_database_fks.sql'],
    'otp_database': ['otp_hash_and_attempts.sql', 'otp_email_delivery.sql', 'otp_remove_cross_database_fk.sql'],
}


def main():
    for name, files in MIGRATIONS.items():
        try:
            with database(name) as conn:
                for filename in files:
                    conn.execute((ROOT / filename).read_text(encoding='utf-8'))
            print(f'[OK] {name}: {", ".join(files)}')
        except Exception as exc:
            print(f'[LỖI] {name}: {type(exc).__name__}. Dừng tại đây; không chạy lại schema CREATE TABLE trên database có dữ liệu.')
            return 1
    print('Đã áp dụng migration. Chạy python check_schema.py để xác nhận.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

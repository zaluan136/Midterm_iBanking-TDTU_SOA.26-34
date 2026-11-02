"""Add demo data without resetting existing accounts or balances."""
import bcrypt
from services.common import database


def main():
    password_hash = bcrypt.hashpw(b'Demo123!', bcrypt.gensalt()).decode()
    with database('auth_database') as conn:
        for username, name, balance in [('alice', 'Nguyen Van A', 10000000), ('bob', 'Tran Thi B', 5000000), ('charlie', 'Le Van C', 3000000)]:
            conn.execute('INSERT INTO app_user (username,password_hash,full_name,phone,email,balance) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING', (username, password_hash, name, '0901111111', f'{username}@example.com', balance))
            # Repair only the placeholder hash shipped with the original seed.
            conn.execute('UPDATE app_user SET password_hash=%s WHERE username=%s AND password_hash=%s', (password_hash, username, '$2b$12$...'))
    with database('tuition_database') as conn:
        conn.execute('LOCK TABLE tuition_fee IN SHARE ROW EXCLUSIVE MODE')
        for mssv, name, amount, status in [('SV001','Nguyen Van A',5000000,'unpaid'), ('SV002','Tran Thi B',4500000,'unpaid'), ('SV003','Le Van C',6000000,'unpaid'), ('SV004','Pham Thi D',5500000,'paid')]:
            conn.execute('INSERT INTO tuition_fee (mssv,student_name,amount,semester,status) SELECT %s,%s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM tuition_fee WHERE mssv=%s AND semester=%s)', (mssv,name,amount,'HK1-2026',status,mssv,'HK1-2026'))
    print('Đã nạp dữ liệu demo. Tài khoản mới: alice / bob / charlie; mật khẩu: Demo123!')


if __name__ == '__main__':
    main()

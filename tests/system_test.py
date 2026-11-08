"""Isolated PostgreSQL integration checks; Gmail is replaced with an in-memory mailbox.

Requires permission to create/drop schemas in each configured database.
Run: python tests/system_test.py
"""
import asyncio
import os
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bcrypt
import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from services.config import load_connections


async def exercise():
    from services import auth_account, common, otp, payment, tuition

    mailbox = []
    async def fake_email(recipient, subject, content, html_content):
        mailbox.append((recipient, subject, content))
    otp.send_email = fake_email
    apps = {'auth_account': auth_account.app, 'tuition': tuition.app, 'otp': otp.app}
    async def routed(service, port, method, path, body=None):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=apps[service]), base_url='http://test') as client:
            response = await client.request(method, path, headers={'X-Service-Token': os.environ['SERVICE_TOKEN']}, json=body)
        if response.is_error:
            raise payment.HTTPException(response.status_code, response.json().get('detail'))
        return response.json()
    payment.call_service = routed

    def insert(name, query, args=()):
        with common.database(name) as conn:
            row = conn.execute(query, args).fetchone()
        return row['id']
    password = bcrypt.hashpw(b'password', bcrypt.gensalt()).decode()
    users = [insert('auth_database', 'INSERT INTO app_user (username,password_hash,full_name,email,balance) VALUES (%s,%s,%s,%s,%s) RETURNING id',
                    (f'user{i}', password, f'User {i}', f'user{i}@example.com', 100)) for i in range(3)]
    def fee(mssv, amount):
        return insert('tuition_database', "INSERT INTO tuition_fee (mssv,student_name,amount,semester) VALUES (%s,'Student',%s,'HK1') RETURNING id", (mssv, amount))
    async def client_for(app, method, path, **kwargs):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            return await client.request(method, path, **kwargs)
    login = await client_for(auth_account.app, 'POST', '/api/auth/login', json={'username':'user0','password':'password'})
    assert login.status_code == 200
    tokens = [common.token_for(uid) for uid in users]
    async def api(user, method, path, **kwargs):
        return await client_for(payment.app, method, path, headers={'Authorization': 'Bearer ' + tokens[user]}, **kwargs)
    async def start(user, fee_id):
        res = await api(user, 'POST', '/api/payments', json={'tuition_fee_id':fee_id})
        assert res.status_code == 201, res.text
        code = re.search(r'là (\d{6})\.', mailbox[-1][2]).group(1)
        return res.json()['transaction_code'], code
    async def confirm(user, tx, code):
        return await api(user, 'POST', f'/api/payments/{tx}/confirm', json={'code':code})

    f1 = fee('TEST1', 10)
    lookup = await client_for(tuition.app, 'GET', '/api/tuition/TEST1', headers={'Authorization':'Bearer '+tokens[0]})
    assert lookup.status_code == 200 and lookup.json()[0]['id'] == f1
    tx, code = await start(0, f1)
    assert (await confirm(0, tx, '999999' if code != '999999' else '000000')).status_code == 400
    assert (await confirm(0, tx, code)).json()['status'] == 'success'
    replay = await routed('otp', 8004, 'GET', f"/internal/otp/{payment.get_transaction(tx)['id']}/verified")
    assert replay['verified']
    try:
        await routed('otp', 8004, 'POST', '/internal/otp/verify', {'transaction_id':payment.get_transaction(tx)['id'], 'code':code})
        raise AssertionError('OTP replay accepted')
    except payment.HTTPException as exc:
        assert exc.status_code == 400
    assert (await api(0, 'GET', '/api/account/transactions')).json()[0]['status'] == 'success'
    print('PASS login, lookup, wrong OTP, payment, history, OTP replay', flush=True)

    # A crash after OTP verification but before Payment updates its own status.
    f2 = fee('TEST2', 10)
    tx2, code2 = await start(0, f2)
    await routed('otp', 8004, 'POST', '/internal/otp/verify', {'transaction_id':payment.get_transaction(tx2)['id'], 'code':code2})
    await payment.recover_payments()
    assert payment.get_transaction(tx2)['status'] == 'success'
    print('PASS recovery after OTP verification', flush=True)

    # Recovery after the debit is reserved and the service stops.
    f3 = fee('TEST3', 10)
    tx3, code3 = await start(0, f3)
    await routed('otp', 8004, 'POST', '/internal/otp/verify', {'transaction_id':payment.get_transaction(tx3)['id'], 'code':code3})
    await payment.set_status(tx3, 'processing')
    await routed('auth_account', 8001, 'POST', f'/internal/accounts/{users[0]}/reserve', {'transaction_code':tx3,'amount':'10'})
    await payment.recover_payments()
    assert payment.get_transaction(tx3)['status'] == 'success'
    print('PASS recovery after reservation', flush=True)

    # The tuition update succeeded but Payment stopped before committing.
    f4 = fee('TEST4', 10)
    tx4, code4 = await start(0, f4)
    await routed('otp', 8004, 'POST', '/internal/otp/verify', {'transaction_id':payment.get_transaction(tx4)['id'], 'code':code4})
    await payment.set_status(tx4, 'processing')
    await routed('auth_account', 8001, 'POST', f'/internal/accounts/{users[0]}/reserve', {'transaction_code':tx4,'amount':'10'})
    await routed('tuition', 8003, 'POST', f'/internal/tuition/{f4}/pay', {'transaction_code':tx4})
    await payment.recover_payments()
    assert payment.get_transaction(tx4)['status'] == 'success'
    print('PASS recovery after tuition update', flush=True)

    # Expired OTP must never advance a transaction.
    tx_expired, expired_code = await start(2, fee('EXPIRED', 10))
    expired_id = payment.get_transaction(tx_expired)['id']
    with common.database('otp_database') as conn:
        conn.execute("UPDATE otp SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 minute' WHERE transaction_id = %s", (expired_id,))
    assert (await confirm(2, tx_expired, expired_code)).status_code == 400
    await payment.recover_payments()
    assert payment.get_transaction(tx_expired)['status'] == 'pending_otp'
    print('PASS expired OTP rejected', flush=True)

    # Two payments compete for the same remaining balance.
    a, b = await start(1, fee('A', 70)), await start(1, fee('B', 70))
    result = await asyncio.gather(confirm(1, *a), confirm(1, *b))
    assert sorted(r.status_code for r in result) == [200, 409], [r.text for r in result]
    with common.database('auth_database') as conn:
        assert conn.execute('SELECT balance FROM app_user WHERE id=%s', (users[1],)).fetchone()['balance'] == 30
    print('PASS concurrent payments on one balance', flush=True)

    # Two users compete for one fee; losing reservation must be released.
    shared = fee('SHARED', 40)
    a, b = await start(0, shared), await start(2, shared)
    result = await asyncio.gather(confirm(0, *a), confirm(2, *b))
    assert sorted(r.status_code for r in result) == [200, 409], [r.text for r in result]
    with common.database('auth_database') as conn:
        balances = conn.execute('SELECT id,balance FROM app_user WHERE id IN (%s,%s)', (users[0],users[2])).fetchall()
    assert sum(row['balance'] for row in balances) == 120
    print('PASS concurrent users paying one fee', flush=True)
    common.close_database_pools()


def main():
    names = ('auth_database', 'payment_database', 'tuition_database', 'otp_database')
    configured = {name: os.getenv(name.upper() + '_URL') for name in names}
    file_connections = load_connections() if any(not value for value in configured.values()) else {}
    connections = {name: configured[name] or file_connections[name] for name in names}
    schema = 'system_test_' + uuid.uuid4().hex
    created = []
    try:
        for name, url in connections.items():
            settings = conninfo_to_dict(url)
            # Never change session state on a shared Neon transaction pooler.
            if settings.get('host', '').endswith('.neon.tech'):
                settings['host'] = settings['host'].replace('-pooler.', '.')
            direct_url = make_conninfo(**settings)
            with psycopg.connect(direct_url) as conn:
                conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
                conn.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(schema)))
                filename = {'auth_database':'auth_account_db.sql','payment_database':'payment_db.sql',
                            'tuition_database':'tuition_db.sql','otp_database':'otp_db.sql'}[name]
                conn.execute((ROOT / 'DB' / 'sql' / filename).read_text(encoding='utf-8'))
            created.append(direct_url)
            os.environ[name.upper() + '_URL'] = direct_url
        os.environ['DB_SCHEMA'] = schema
        os.environ.update(JWT_SECRET='test-jwt-secret-' * 4, SERVICE_TOKEN='test-service-secret', OTP_SECRET='test-otp-secret')
        asyncio.run(exercise())
    finally:
        from services.common import close_database_pools
        close_database_pools()
        for url in created:
            with psycopg.connect(url, autocommit=True) as conn:
                conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
        print('Test schemas removed', flush=True)


if __name__ == '__main__':
    main()

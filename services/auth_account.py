import bcrypt
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from services.common import make_app, database, token_for, current_user

app = make_app('iBanking Auth–Account')


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)


@app.post('/api/auth/login')
def login(body: Login):
    with database('auth_database') as conn:
        user = conn.execute('SELECT id, full_name, password_hash FROM app_user WHERE username = %s', (body.username,)).fetchone()
    valid = False
    if user and len(body.password.encode()) <= 72:
        try:
            valid = bcrypt.checkpw(body.password.encode(), user['password_hash'].encode())
        except ValueError:
            pass
    if not valid:
        raise HTTPException(401, 'Sai username hoặc password')
    return {'token': token_for(user['id']), 'user_id': user['id'], 'full_name': user['full_name']}


@app.get('/api/account/info')
def account(user_id: int = Depends(current_user)):
    with database('auth_database') as conn:
        user = conn.execute('SELECT id, full_name, phone, email, balance FROM app_user WHERE id = %s', (user_id,)).fetchone()
    if not user:
        raise HTTPException(404, 'Không tìm thấy tài khoản')
    user['balance'] = str(user['balance'])
    return user


from services.internal_payment import MoneyOperation, internal_auth


@app.post('/internal/account/{operation}', dependencies=[Depends(internal_auth)])
def money_operation(operation: str, body: MoneyOperation):
    if operation not in ('deduct', 'refund'):
        raise HTTPException(404)
    with database('auth_database') as conn:
        user = conn.execute('SELECT balance FROM app_user WHERE id=%s FOR UPDATE', (body.user_id,)).fetchone()
        if not user:
            raise HTTPException(404, 'Không tìm thấy tài khoản')
        record = conn.execute('SELECT * FROM account_payment WHERE transaction_code=%s', (body.transaction_code,)).fetchone()
        if record and (record['user_id'] != body.user_id or record['amount'] != body.amount):
            raise HTTPException(409, 'Giao dịch không khớp')
        if operation == 'deduct' and not record:
            if user['balance'] < body.amount:
                raise HTTPException(409, 'Số dư không đủ')
            conn.execute('UPDATE app_user SET balance=balance-%s, version=version+1 WHERE id=%s', (body.amount,body.user_id))
            conn.execute('INSERT INTO account_payment(transaction_code,user_id,amount) VALUES (%s,%s,%s)', (body.transaction_code,body.user_id,body.amount))
        elif operation == 'refund' and record and not record['refunded']:
            conn.execute('UPDATE app_user SET balance=balance+%s, version=version+1 WHERE id=%s', (body.amount,body.user_id))
            conn.execute('UPDATE account_payment SET refunded=TRUE WHERE transaction_code=%s', (body.transaction_code,))
        return {'ok': True}

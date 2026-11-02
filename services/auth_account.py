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

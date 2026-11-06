import os
import bcrypt
from decimal import Decimal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from services.common import current_user, database

def demo_access(user: int = Depends(current_user)):
    if os.getenv('DEMO_ADMIN') != '1': raise HTTPException(404)

class AccountData(BaseModel):
    id: int | None = Field(default=None, gt=0)
    username: str = Field(min_length=1,max_length=50,pattern=r'^\S+$')
    full_name: str = Field(min_length=1,max_length=100)
    email: EmailStr
    phone: str = Field(default='',max_length=15)
    balance: Decimal = Field(ge=0,max_digits=15,decimal_places=2)
    password: str = Field(default='',max_length=72)

class TuitionData(BaseModel):
    mssv: str = Field(min_length=1,max_length=20)
    student_name: str = Field(min_length=1,max_length=100)
    semester: str = Field(min_length=1,max_length=50)
    amount: Decimal = Field(gt=0,max_digits=15,decimal_places=2)

def attach_accounts(app):
    @app.get('/api/demo/accounts', dependencies=[Depends(demo_access)])
    def accounts():
        with database('auth_database') as conn:
            rows=conn.execute('SELECT id,username,full_name,email,phone,balance FROM app_user ORDER BY id').fetchall()
        for row in rows: row['balance']=str(row['balance'])
        return rows

    @app.post('/api/demo/accounts', dependencies=[Depends(demo_access)])
    def save(body: AccountData):
        password=body.password.encode()
        if len(password)>72 or (password and len(password)<6): raise HTTPException(422,'Mật khẩu cần từ 6 đến 72 byte')
        with database('auth_database') as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('demo:'+body.username,))
            row=conn.execute('SELECT id FROM app_user WHERE id=%s FOR UPDATE',(body.id,)).fetchone() if body.id else None
            if body.id and not row: raise HTTPException(404,'Tài khoản không tồn tại')
            duplicate=conn.execute('SELECT id FROM app_user WHERE username=%s',(body.username,)).fetchone()
            if duplicate and duplicate['id'] != body.id: raise HTTPException(409,'Username đã được sử dụng; chọn tài khoản để sửa hoặc nhập tên khác')
            if row:
                if conn.execute("SELECT 1 FROM account_reservation WHERE user_id=%s AND status='reserved'",(row['id'],)).fetchone(): raise HTTPException(409,'Đang giữ tiền; hãy hoàn tất giao dịch trước khi sửa')
                conn.execute('UPDATE app_user SET username=%s,full_name=%s,email=%s,phone=%s,balance=%s,version=version+1 WHERE id=%s',(body.username,body.full_name,str(body.email),body.phone,body.balance,row['id']))
                if password: conn.execute('UPDATE app_user SET password_hash=%s WHERE id=%s',(bcrypt.hashpw(password,bcrypt.gensalt()).decode(),row['id']))
            else:
                if not password: raise HTTPException(422,'Tài khoản mới cần mật khẩu')
                conn.execute('INSERT INTO app_user(username,password_hash,full_name,email,phone,balance) VALUES(%s,%s,%s,%s,%s,%s)',(body.username,bcrypt.hashpw(password,bcrypt.gensalt()).decode(),body.full_name,str(body.email),body.phone,body.balance))
        return {'saved':True}

def attach_tuition(app):
    @app.post('/api/demo/tuition', dependencies=[Depends(demo_access)])
    def add(body: TuitionData):
        with database('tuition_database') as conn:
            return conn.execute("INSERT INTO tuition_fee(mssv,student_name,semester,amount,status) VALUES(%s,%s,%s,%s,'unpaid') RETURNING id",(body.mssv.strip(),body.student_name,body.semester,body.amount)).fetchone()

import os
from uuid import uuid4
from decimal import Decimal
import httpx
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field
from services.common import make_app, database, current_user

app = make_app('iBanking Payment — demo OTP')


def call(port, path, body=None, authorization=''):
    try:
        r = httpx.request('POST' if body else 'GET', f'http://127.0.0.1:{port}{path}', json=body, headers={'X-Internal-Key': os.environ.get('INTERNAL_KEY',''), 'Authorization': authorization}, timeout=12)
    except httpx.RequestError:
        raise HTTPException(503, 'Kết nối gián đoạn. Giao dịch được giữ lại; hãy thử xác nhận lại.')
    if r.is_error:
        raise HTTPException(r.status_code, r.json().get('detail', 'Service gặp lỗi'))
    return r.json()


class Create(BaseModel):
    tuition_fee_id: int = Field(gt=0)


class Verify(BaseModel):
    transaction_id: int = Field(gt=0)
    otp_code: str


@app.post('/api/payment/create', status_code=201)
def create(body: Create, request: Request, user: int = Depends(current_user)):
    fee = call(8003, f'/internal/tuition/{body.tuition_fee_id}')
    account = call(8001, '/api/account/info', authorization=request.headers.get('Authorization',''))
    if fee['status'] != 'unpaid':
        raise HTTPException(409, 'Khoản học phí đã thanh toán')
    if Decimal(account['balance']) < Decimal(fee['amount']):
        raise HTTPException(409, 'Số dư không đủ')
    with database('payment_database') as conn:
        conn.execute('SELECT pg_advisory_xact_lock(%s)', (user,))
        conn.execute("UPDATE payment_transaction SET status='expired',completed_at=CURRENT_TIMESTAMP WHERE payer_user_id=%s AND status='pending_otp' AND created_at < CURRENT_TIMESTAMP - INTERVAL '5 minutes'", (user,))
        pending = conn.execute("SELECT id FROM payment_transaction WHERE payer_user_id=%s AND status IN ('pending_otp','processing')", (user,)).fetchone()
        if pending:
            return {'transaction_id': pending['id'], 'message': 'Tiếp tục giao dịch đang chờ'}
        row = conn.execute("INSERT INTO payment_transaction(transaction_code,payer_user_id,tuition_fee_id,amount) VALUES (%s,%s,%s,%s) RETURNING id", ('TXN_'+uuid4().hex,user,body.tuition_fee_id,fee['amount'])).fetchone()
    return {'transaction_id': row['id'], 'status': 'pending_otp'}


@app.get('/api/payment/history')
def history(user: int = Depends(current_user)):
    with database('payment_database') as conn:
        return conn.execute('SELECT * FROM payment_transaction WHERE payer_user_id=%s ORDER BY id DESC', (user,)).fetchall()


@app.post('/api/payment/verify-otp')
def verify(body: Verify, user: int = Depends(current_user)):
    if os.environ.get('DEMO_OTP') != '1':
        raise HTTPException(503, 'Chưa bật chế độ OTP thử')
    if body.otp_code != '123456':
        raise HTTPException(400, 'OTP thử là 123456')
    with database('payment_database') as conn:
        row = conn.execute('SELECT *, created_at < CURRENT_TIMESTAMP - INTERVAL \'5 minutes\' AS expired FROM payment_transaction WHERE id=%s AND payer_user_id=%s FOR UPDATE', (body.transaction_id,user)).fetchone()
        if not row:
            raise HTTPException(404, 'Không tìm thấy giao dịch')
        if row['status'] == 'pending_otp':
            status = 'expired' if row['expired'] else 'processing'
            conn.execute('UPDATE payment_transaction SET status=%s WHERE id=%s', (status,row['id']))
    with database('payment_database') as conn:
        row = conn.execute('SELECT * FROM payment_transaction WHERE id=%s FOR UPDATE', (body.transaction_id,)).fetchone()
        if row['status'] != 'processing':
            return {'transaction_id': row['id'], 'status': row['status']}
        money = {'transaction_code': row['transaction_code'], 'user_id': user, 'amount': str(row['amount'])}
        try:
            call(8001, '/internal/account/deduct', money)
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
            status = 'failed'
        else:
            try:
                call(8003, '/internal/tuition/mark-paid', {'transaction_code':row['transaction_code'],'tuition_fee_id':row['tuition_fee_id'],'amount':str(row['amount'])})
                status = 'success'
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise
                call(8001, '/internal/account/refund', money)
                status = 'refunded'
        conn.execute('UPDATE payment_transaction SET status=%s,completed_at=CURRENT_TIMESTAMP WHERE id=%s', (status,row['id']))
    return {'transaction_id': row['id'], 'status': status}

import os
import secrets
from decimal import Decimal

import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from services.common import current_user, database, make_app, require_service_token

app = make_app('iBanking Payment')


class StartPayment(BaseModel):
    tuition_fee_id: int = Field(gt=0)


class ConfirmPayment(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')


def internal_headers():
    token = os.environ.get('SERVICE_TOKEN')
    if not token:
        raise HTTPException(503, 'Thiếu cấu hình xác thực giữa các service')
    return {'X-Service-Token': token}


async def call_service(service: str, port: int, method: str, path: str, body=None):
    base_url = os.getenv(f'{service.upper()}_SERVICE_URL', f'http://127.0.0.1:{port}')
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(method, base_url + path, headers=internal_headers(), json=body)
    except httpx.RequestError:
        raise HTTPException(503, f'{service} service chưa sẵn sàng; giao dịch có thể được tiếp tục bằng cách thử lại.')
    try:
        data = response.json()
    except ValueError:
        data = {'detail': 'Service trả về phản hồi không hợp lệ'}
    if response.is_error:
        detail = data.get('detail', 'Không xử lý được yêu cầu ở service phụ thuộc') if isinstance(data, dict) else 'Service phụ thuộc gặp lỗi'
        raise HTTPException(response.status_code, detail)
    return data


def get_transaction(transaction_code: str, user_id: int | None = None):
    with database('payment_database') as conn:
        if user_id is None:
            row = conn.execute('SELECT * FROM payment_transaction WHERE transaction_code = %s', (transaction_code,)).fetchone()
        else:
            row = conn.execute(
                'SELECT * FROM payment_transaction WHERE transaction_code = %s AND payer_user_id = %s',
                (transaction_code, user_id),
            ).fetchone()
    if not row:
        raise HTTPException(404, 'Không tìm thấy giao dịch')
    row['amount'] = str(row['amount'])
    return row


async def ensure_receipt_email(transaction: dict):
    if transaction.get('email_sent'):
        return True
    try:
        payer = await call_service('auth_account', 8001, 'GET', f"/internal/accounts/{transaction['payer_user_id']}")
        fee = await call_service('tuition', 8003, 'GET', f"/internal/tuition/{transaction['tuition_fee_id']}")
        await call_service(
            'otp', 8004, 'POST', '/internal/email/receipt',
            {
                'transaction_code': transaction['transaction_code'],
                'recipient': payer['email'],
                'student_id': fee['mssv'],
                'student_name': fee['student_name'],
                'semester': fee['semester'],
                'amount': transaction['amount'],
            },
        )
        with database('payment_database') as conn:
            conn.execute('UPDATE payment_transaction SET email_sent = TRUE WHERE transaction_code = %s', (transaction['transaction_code'],))
        return True
    except HTTPException:
        # Email delivery failure must not undo an already completed payment.
        return False


@app.post('/api/payments', status_code=201)
async def start_payment(body: StartPayment, user_id: int = Depends(current_user)):
    fee = await call_service('tuition', 8003, 'GET', f'/internal/tuition/{body.tuition_fee_id}')
    if fee['status'] != 'unpaid':
        raise HTTPException(409, 'Khoản học phí này đã được thanh toán')
    payer = await call_service('auth_account', 8001, 'GET', f'/internal/accounts/{user_id}')
    amount = Decimal(fee['amount'])
    if Decimal(payer['balance']) < amount:
        raise HTTPException(409, 'Số dư khả dụng không đủ')

    transaction_code = secrets.token_urlsafe(24)
    with database('payment_database') as conn:
        transaction = conn.execute(
            "INSERT INTO payment_transaction (transaction_code, payer_user_id, tuition_fee_id, amount, status) "
            "VALUES (%s, %s, %s, %s, 'pending_otp') "
            'RETURNING id, transaction_code, payer_user_id, tuition_fee_id, amount, status, created_at',
            (transaction_code, user_id, fee['id'], amount),
        ).fetchone()
    transaction['amount'] = str(transaction['amount'])
    masked_email = payer['email']
    if '@' in masked_email:
        name, domain = masked_email.split('@', 1)
        masked_email = (name[:1] + '***' if len(name) > 1 else '*') + '@' + domain
    try:
        await call_service('otp', 8004, 'POST', '/internal/otp', {'transaction_id': transaction['id'], 'transaction_code': transaction_code, 'recipient': payer['email']})
        transaction['otp_sent'] = True
        transaction['email'] = masked_email
    except HTTPException as exc:
        # Keep a durable pending transaction so the caller can retry OTP delivery.
        transaction['otp_sent'] = False
        transaction['otp_error'] = exc.detail
    return transaction


@app.post('/api/payments/{transaction_code}/otp/resend')
async def resend_otp(transaction_code: str, user_id: int = Depends(current_user)):
    transaction = get_transaction(transaction_code, user_id)
    if transaction['status'] != 'pending_otp':
        raise HTTPException(409, 'Giao dịch không còn chờ OTP')
    payer = await call_service('auth_account', 8001, 'GET', f"/internal/accounts/{transaction['payer_user_id']}")
    result = await call_service('otp', 8004, 'POST', '/internal/otp', {'transaction_id': transaction['id'], 'transaction_code': transaction_code, 'recipient': payer['email']})
    return {'transaction_code': transaction_code, **result}


async def set_status(transaction_code: str, status: str, completed: bool = False):
    with database('payment_database') as conn:
        conn.execute(
            'UPDATE payment_transaction SET status = %s, completed_at = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE completed_at END '
            'WHERE transaction_code = %s',
            (status, completed, transaction_code),
        )


@app.post('/api/payments/{transaction_code}/confirm')
async def confirm_payment(transaction_code: str, body: ConfirmPayment, user_id: int = Depends(current_user)):
    transaction = get_transaction(transaction_code, user_id)
    if transaction['status'] == 'success':
        transaction['email_sent'] = await ensure_receipt_email(transaction)
        return transaction
    if transaction['status'] in ('failed', 'expired', 'refunded'):
        raise HTTPException(409, f"Giao dịch đang ở trạng thái {transaction['status']}")

    if transaction['status'] == 'pending_otp':
        await call_service('otp', 8004, 'POST', '/internal/otp/verify', {'transaction_id': transaction['id'], 'code': body.code})
        # A retry after this point resumes the idempotent steps below without reusing the OTP.
        await set_status(transaction_code, 'processing')

    reserve_body = {'transaction_code': transaction_code, 'amount': transaction['amount']}
    try:
        await call_service('auth_account', 8001, 'POST', f"/internal/accounts/{user_id}/reserve", reserve_body)
    except HTTPException as exc:
        if exc.status_code == 409:
            await set_status(transaction_code, 'failed', completed=True)
        raise

    try:
        await call_service(
            'tuition', 8003, 'POST', f"/internal/tuition/{transaction['tuition_fee_id']}/pay",
            {'transaction_code': transaction_code},
        )
    except HTTPException as exc:
        if exc.status_code in (404, 409):
            await call_service('auth_account', 8001, 'POST', f'/internal/accounts/reservations/{transaction_code}/release')
            await set_status(transaction_code, 'failed', completed=True)
        raise

    await call_service('auth_account', 8001, 'POST', f'/internal/accounts/reservations/{transaction_code}/commit')
    await set_status(transaction_code, 'success', completed=True)
    transaction = get_transaction(transaction_code, user_id)
    transaction['email_sent'] = await ensure_receipt_email(transaction)
    return transaction


@app.post('/api/payments/{transaction_code}/receipt/resend')
async def resend_receipt(transaction_code: str, user_id: int = Depends(current_user)):
    transaction = get_transaction(transaction_code, user_id)
    if transaction['status'] != 'success':
        raise HTTPException(409, 'Chỉ gửi biên nhận cho giao dịch thành công')
    sent = await ensure_receipt_email(transaction)
    if not sent:
        raise HTTPException(503, 'Giao dịch thành công nhưng email chưa gửi được; có thể thử lại sau.')
    return {'transaction_code': transaction_code, 'email_sent': True}


@app.get('/api/payments/{transaction_code}')
def payment_status(transaction_code: str, user_id: int = Depends(current_user)):
    return get_transaction(transaction_code, user_id)


@app.get('/api/account/transactions')
def payment_history(user_id: int = Depends(current_user), limit: int = 50, offset: int = 0):
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(422, 'limit phải từ 1 đến 100 và offset không được âm')
    with database('payment_database') as conn:
        rows = conn.execute(
            'SELECT transaction_code, tuition_fee_id, amount, status, created_at, completed_at '
            'FROM payment_transaction WHERE payer_user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s',
            (user_id, limit, offset),
        ).fetchall()
    for row in rows:
        row['amount'] = str(row['amount'])
    return rows


@app.get('/internal/payments/{transaction_code}', dependencies=[Depends(require_service_token)])
def internal_payment_status(transaction_code: str):
    return get_transaction(transaction_code)

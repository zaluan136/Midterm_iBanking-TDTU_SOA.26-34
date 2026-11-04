import base64
import hashlib
import hmac
import os
import secrets
from email.message import EmailMessage

import httpx
from fastapi import Depends, HTTPException
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field

from services.common import database, make_app, require_service_token

app = make_app('iBanking OTP and email')


class CreateOTP(BaseModel):
    transaction_id: int = Field(gt=0)
    transaction_code: str = Field(min_length=1, max_length=64)
    recipient: EmailStr


class VerifyOTP(BaseModel):
    transaction_id: int = Field(gt=0)
    code: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')


class ReceiptEmail(BaseModel):
    transaction_code: str = Field(min_length=1, max_length=64)
    recipient: EmailStr
    student_id: str = Field(min_length=1, max_length=20)
    student_name: str = Field(min_length=1, max_length=100)
    semester: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


def code_hash(code: str) -> str:
    pepper = os.getenv('OTP_SECRET') or os.getenv('SERVICE_TOKEN')
    if not pepper:
        raise HTTPException(503, 'Chưa cấu hình khóa bảo vệ OTP.')
    return hmac.new(pepper.encode(), code.encode('ascii'), hashlib.sha256).hexdigest()


async def send_email(recipient: str, subject: str, content: str):
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    refresh_token = os.getenv('GOOGLE_REFRESH_TOKEN')
    sender = os.getenv('GMAIL_SENDER')
    if not all((client_id, client_secret, refresh_token, sender)):
        raise HTTPException(503, 'Chưa cấu hình Gmail API; kiểm tra biến môi trường Google OAuth.')

    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            },
        )
        if token_response.is_error:
            raise HTTPException(503, 'Không lấy được quyền gửi email từ Google.')
        access_token = token_response.json().get('access_token')
        if not access_token:
            raise HTTPException(503, 'Google không trả access token gửi email.')

        message = EmailMessage()
        message['To'] = recipient
        message['From'] = sender
        message['Subject'] = subject
        message.set_content(content)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
        response = await client.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={'Authorization': f'Bearer {access_token}'},
            json={'raw': raw},
        )
        if response.is_error:
            raise HTTPException(503, 'Gmail API không gửi được email; vui lòng thử lại.')


@app.post('/internal/otp', dependencies=[Depends(require_service_token)])
async def create_otp(body: CreateOTP):
    code = f'{secrets.randbelow(1_000_000):06d}'
    digest = code_hash(code)
    with database('otp_database') as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('global-active-otp-code', 0))")
        conn.execute(
            'UPDATE otp SET used = TRUE WHERE transaction_id = %s AND used = FALSE AND expires_at <= CURRENT_TIMESTAMP',
            (body.transaction_id,),
        )
        sent_recently = conn.execute(
            "SELECT COUNT(*) AS n FROM otp WHERE transaction_id = %s AND created_at > CURRENT_TIMESTAMP - INTERVAL '15 minutes'",
            (body.transaction_id,),
        ).fetchone()['n']
        if sent_recently >= 5:
            raise HTTPException(429, 'Đã gửi quá nhiều OTP cho giao dịch này. Vui lòng thử lại sau.')
        conn.execute('UPDATE otp SET used = TRUE WHERE transaction_id = %s AND used = FALSE', (body.transaction_id,))
        # The đề requires active codes to be unique across concurrent transactions.
        active = conn.execute(
            'SELECT 1 FROM otp WHERE otp_code = %s AND used = FALSE AND expires_at > CURRENT_TIMESTAMP LIMIT 1',
            (digest,),
        ).fetchone()
        while active:
            code = f'{secrets.randbelow(1_000_000):06d}'
            digest = code_hash(code)
            active = conn.execute(
                'SELECT 1 FROM otp WHERE otp_code = %s AND used = FALSE AND expires_at > CURRENT_TIMESTAMP LIMIT 1',
                (digest,),
            ).fetchone()
        conn.execute(
            "INSERT INTO otp (otp_code, transaction_id, expires_at, used, attempt_count) "
            "VALUES (%s, %s, CURRENT_TIMESTAMP + INTERVAL '5 minutes', FALSE, 0)",
            (digest, body.transaction_id),
        )

    try:
        await send_email(
            str(body.recipient),
            'Mã OTP xác nhận thanh toán học phí',
            f'Mã OTP của giao dịch {body.transaction_code} là {code}. Mã có hiệu lực trong 5 phút và chỉ dùng một lần.',
        )
    except HTTPException:
        with database('otp_database') as conn:
            conn.execute('UPDATE otp SET used = TRUE WHERE transaction_id = %s AND otp_code = %s AND used = FALSE', (body.transaction_id, digest))
        raise
    except httpx.RequestError:
        with database('otp_database') as conn:
            conn.execute('UPDATE otp SET used = TRUE WHERE transaction_id = %s AND otp_code = %s AND used = FALSE', (body.transaction_id, digest))
        raise HTTPException(503, 'Không kết nối được Gmail API; vui lòng gửi lại OTP.')
    return {'sent': True, 'expires_in_seconds': 300}


@app.post('/internal/email/receipt', dependencies=[Depends(require_service_token)])
async def send_receipt(body: ReceiptEmail):
    with database('otp_database') as conn:
        conn.execute(
            "INSERT INTO email_delivery (transaction_code, recipient, status) VALUES (%s, %s, 'pending') "
            'ON CONFLICT (transaction_code) DO NOTHING',
            (body.transaction_code, str(body.recipient)),
        )
        delivery = conn.execute(
            'SELECT recipient, status FROM email_delivery WHERE transaction_code = %s FOR UPDATE',
            (body.transaction_code,),
        ).fetchone()
        if delivery['recipient'] != str(body.recipient):
            raise HTTPException(409, 'Mã giao dịch đã gắn với email khác')
        if delivery['status'] == 'sent':
            return {'sent': True, 'already_sent': True}

    await send_email(
        str(body.recipient),
        'Xác nhận thanh toán học phí thành công',
        f"Giao dịch {body.transaction_code} đã thanh toán thành công.\n"
        f"Sinh viên: {body.student_name} ({body.student_id})\n"
        f"Học kỳ: {body.semester}\nSố tiền: {body.amount} VND",
    )
    with database('otp_database') as conn:
        conn.execute(
            "UPDATE email_delivery SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE transaction_code = %s",
            (body.transaction_code,),
        )
    return {'sent': True, 'already_sent': False}


@app.post('/internal/otp/verify', dependencies=[Depends(require_service_token)])
def verify_otp(body: VerifyOTP):
    failure = None
    with database('otp_database') as conn:
        row = conn.execute(
            'SELECT id, otp_code, expires_at, used, verified, attempt_count, expires_at <= CURRENT_TIMESTAMP AS expired '
            'FROM otp WHERE transaction_id = %s AND used = FALSE ORDER BY created_at DESC LIMIT 1 FOR UPDATE',
            (body.transaction_id,),
        ).fetchone()
        if not row:
            # A payment retry may arrive after OTP was consumed but before the
            # payment service persisted its processing state. Permit only the
            # same code for that same transaction to resume the saga.
            consumed = conn.execute(
                'SELECT otp_code, verified FROM otp WHERE transaction_id = %s ORDER BY created_at DESC LIMIT 1',
                (body.transaction_id,),
            ).fetchone()
            if consumed and consumed['verified'] and secrets.compare_digest(consumed['otp_code'], code_hash(body.code)):
                return {'valid': True, 'replayed': True}
            failure = 'OTP không hợp lệ hoặc đã được sử dụng'
        elif row['expired']:
            conn.execute('UPDATE otp SET used = TRUE WHERE id = %s', (row['id'],))
            failure = 'OTP đã hết hạn'
        elif row['attempt_count'] >= 5:
            conn.execute('UPDATE otp SET used = TRUE WHERE id = %s', (row['id'],))
            failure = 'OTP đã bị khóa do nhập sai quá số lần'
        elif not secrets.compare_digest(row['otp_code'], code_hash(body.code)):
            next_count = row['attempt_count'] + 1
            conn.execute('UPDATE otp SET attempt_count = %s, used = %s WHERE id = %s', (next_count, next_count >= 5, row['id']))
            failure = 'OTP không chính xác'
        else:
            conn.execute('UPDATE otp SET used = TRUE, verified = TRUE WHERE id = %s', (row['id'],))
    if failure:
        raise HTTPException(400, failure)
    return {'valid': True}

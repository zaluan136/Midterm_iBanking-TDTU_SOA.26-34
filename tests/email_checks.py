"""Focused checks for rendered email and Gmail MIME payload; no email is sent."""
import asyncio
import base64
import os
import sys
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import patch
from unittest.mock import AsyncMock
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.email_templates import otp_html, receipt_html
from services.otp import send_email
from services import otp, payment


class Response:
    is_error = False
    def __init__(self, data): self.data = data
    def json(self): return self.data


class Client:
    payload = None
    def __init__(self, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def post(self, url, **kwargs):
        if url.endswith('/token'): return Response({'access_token': 'test-token'})
        Client.payload = kwargs['json']['raw']
        return Response({'id': 'test-message'})


async def main():
    otp_markup = otp_html('001234', '<txn>')
    receipt = receipt_html('abc<script>', 'SV001', 'Nguyễn <An>', 'HK1', Decimal('1234567.50'))
    assert '001234' in otp_markup and '5 phút' in otp_markup and '&lt;txn&gt;' in otp_markup
    assert 'Nguyễn &lt;An&gt;' in receipt and 'abc&lt;script&gt;' in receipt
    assert '1.234.567,50 VND' in receipt
    assert '1.000 VND' in receipt_html('a', 'b', 'c', 'd', Decimal('1000.00'))
    env = {'GOOGLE_CLIENT_ID':'test', 'GOOGLE_CLIENT_SECRET':'test', 'GOOGLE_REFRESH_TOKEN':'test', 'GMAIL_SENDER':'sender@example.com'}
    with patch.dict(os.environ, env), patch('services.otp.httpx.AsyncClient', Client):
        result = await send_email('recipient@example.com', 'Mã OTP', 'Mã OTP là 001234.', otp_markup)
    assert result == 'test-message'
    message = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(Client.payload))
    assert message.get_content_type() == 'multipart/alternative'
    assert '001234' in message.get_body(preferencelist=('plain',)).get_content()
    assert '001234' in message.get_body(preferencelist=('html',)).get_content()
    print('PASS OTP and receipt HTML, escaped fields, currency, plain-text and HTML MIME')

    class DB:
        def execute(self, query, args=()):
            return self
        def fetchone(self):
            return {'recipient': 'recipient@example.com', 'status': 'sent'}
    @contextmanager
    def fake_database(name):
        yield DB()
    receipt_data = {'transaction_code':'txn', 'recipient':'recipient@example.com', 'student_id':'SV001',
                    'student_name':'An', 'semester':'HK1', 'amount':'10'}
    with patch.object(otp, 'database', fake_database), patch.object(otp, 'send_email', new=AsyncMock()) as send:
        assert (await otp.send_receipt(otp.ReceiptEmail(**receipt_data)))['already_sent']
        send.assert_not_awaited()
        assert not (await otp.send_receipt(otp.ReceiptEmail(**receipt_data, resend=True)))['already_sent']
        send.assert_awaited_once()

    tx = {'transaction_code':'txn', 'payer_user_id':1, 'tuition_fee_id':2, 'amount':'10', 'status':'success', 'email_sent':True}
    async def routed(service, port, method, path, body=None):
        if service == 'auth_account': return {'email':'recipient@example.com'}
        if service == 'tuition': return {'mssv':'SV001', 'student_name':'An', 'semester':'HK1'}
        assert service == 'otp' and body['resend'] is True
        return {'sent':True}
    with patch.object(payment, 'database', fake_database), patch.object(payment, 'call_service', new=AsyncMock(side_effect=routed)) as call:
        assert await payment.ensure_receipt_email(tx)
        call.assert_not_awaited()
        with patch.object(payment, 'get_transaction', return_value=tx):
            assert (await payment.resend_receipt('txn', user_id=1))['email_sent']
        assert call.await_count == 3
    async def failed_delivery(service, port, method, path, body=None):
        if service == 'otp': raise payment.HTTPException(503, 'send failed')
        return await routed(service, port, method, path, body)
    with patch.object(payment, 'database', fake_database), patch.object(payment, 'call_service', new=AsyncMock(side_effect=failed_delivery)), patch.object(payment, 'get_transaction', return_value=tx):
        try:
            await payment.resend_receipt('txn', user_id=1)
        except payment.HTTPException as exc:
            assert exc.status_code == 503
        else:
            raise AssertionError('Failed delivery reported success')
    print('PASS automatic receipt deduplication and explicit resend')


if __name__ == '__main__':
    asyncio.run(main())

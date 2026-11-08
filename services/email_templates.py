"""Email-safe HTML for OTP and tuition payment receipts."""
from decimal import Decimal
from html import escape


def _layout(label: str, title: str, intro: str, content: str) -> str:
    return f'''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f2f5fa;font-family:Arial,sans-serif;color:#122942;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f2f5fa;"><tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #e2e9f3;border-radius:16px;">
<tr><td style="padding:28px 32px;border-bottom:1px solid #eaf0f7;">
<table role="presentation" cellspacing="0" cellpadding="0"><tr><td align="center" width="42" height="42" style="background:#235add;border-radius:12px;color:#ffffff;font-size:18px;font-weight:bold;">iB</td>
<td style="padding-left:12px;"><div style="font-size:19px;font-weight:bold;letter-spacing:-0.5px;">iBanking</div><div style="font-size:10px;color:#718197;letter-spacing:1.4px;">THANH TOÁN HỌC PHÍ</div></td></tr></table>
</td></tr><tr><td style="padding:32px;">
<div style="font-size:11px;font-weight:bold;letter-spacing:1.4px;color:#235add;text-transform:uppercase;">{label}</div>
<h1 style="margin:10px 0 12px;font-size:25px;line-height:1.3;letter-spacing:-0.4px;">{title}</h1>
<p style="margin:0 0 24px;color:#53677e;font-size:15px;line-height:1.6;">{intro}</p>
{content}
</td></tr><tr><td style="padding:20px 32px;border-top:1px solid #eaf0f7;color:#718197;font-size:12px;line-height:1.6;">iBanking · Thanh toán học phí<br>Đây là email tự động, vui lòng không trả lời email này.</td></tr>
</table></td></tr></table></body></html>'''


def otp_html(code: str, transaction_code: str) -> str:
    code, transaction_code = escape(code), escape(transaction_code)
    content = f'''<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#edf4ff;border:1px solid #dce9ff;border-radius:12px;"><tr><td align="center" style="padding:22px 16px;">
<div style="font-size:12px;color:#53677e;">Mã xác thực của bạn</div><div style="margin-top:8px;font-size:34px;line-height:1.3;font-weight:bold;letter-spacing:8px;color:#235add;">{code}</div>
</td></tr></table>
<p style="margin:20px 0 8px;font-size:14px;line-height:1.6;color:#53677e;">Mã có hiệu lực trong <strong style="color:#122942;">5 phút</strong> và chỉ sử dụng một lần. Không chia sẻ mã này với bất kỳ ai.</p>
<p style="margin:0;font-size:13px;line-height:1.6;color:#718197;overflow-wrap:anywhere;word-break:break-all;">Mã giao dịch: {transaction_code}</p>'''
    return _layout('XÁC THỰC GIAO DỊCH', 'Mã OTP của bạn', 'Nhập mã bên dưới để xác nhận thanh toán học phí.', content)


def receipt_html(transaction_code: str, student_id: str, student_name: str, semester: str, amount: Decimal) -> str:
    formatted = f'{amount:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    if formatted.endswith(',00'):
        formatted = formatted[:-3]
    rows = [('Mã giao dịch', transaction_code), ('Sinh viên', student_name), ('MSSV', student_id), ('Học kỳ', semester)]
    details = ''.join(
        f'<tr><td style="padding:10px 0;color:#718197;font-size:13px;vertical-align:top;">{escape(label)}</td>'
        f'<td align="right" style="padding:10px 0;color:#122942;font-size:13px;font-weight:bold;overflow-wrap:anywhere;word-break:break-word;">{escape(value)}</td></tr>'
        for label, value in rows
    )
    content = f'''<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f1faf5;border:1px solid #d6efe0;border-radius:12px;"><tr><td style="padding:20px;">
<div style="font-size:12px;color:#428463;">SỐ TIỀN ĐÃ THANH TOÁN</div><div style="margin-top:6px;color:#18734b;font-size:27px;font-weight:bold;">{formatted} VND</div>
</td></tr></table>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:16px;table-layout:fixed;">{details}</table>'''
    return _layout('GIAO DỊCH THÀNH CÔNG', 'Thanh toán hoàn tất', 'Khoản học phí đã được thanh toán thành công. Thông tin giao dịch của bạn:', content)

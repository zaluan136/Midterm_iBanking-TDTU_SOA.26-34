"""Email-safe HTML for OTP and tuition payment receipts."""

from decimal import Decimal
from html import escape


def _layout(label: str, title: str, intro: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f7fc;font-family:Arial,'Segoe UI',sans-serif;color:#122942;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f7fc;"><tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;"><tr><td style="padding:0 4px 20px;">
<table role="presentation" cellspacing="0" cellpadding="0"><tr><td align="center" width="45" height="45" style="background:#235add;border-radius:14px;color:#ffffff;font-size:18px;font-weight:bold;">iB</td>
<td style="padding-left:13px;"><div style="font-size:21px;font-weight:bold;letter-spacing:-0.7px;color:#122942;">iBanking</div><div style="font-size:9px;font-weight:bold;color:#718197;letter-spacing:1.5px;">CỔNG THANH TOÁN HỌC PHÍ</div></td></tr></table>
</td></tr><tr><td style="background:#ffffff;border:1px solid #e5ebf3;border-radius:20px;padding:32px 24px;">
<div style="font-size:11px;font-weight:bold;letter-spacing:1.2px;color:#235add;">{label}</div>
<h1 style="margin:10px 0 12px;font-size:26px;line-height:1.3;letter-spacing:-0.5px;color:#122942;">{title}</h1>
<p style="margin:0 0 24px;color:#53677e;font-size:15px;line-height:1.6;">{intro}</p>
{content}
</td></tr><tr><td style="padding:20px 4px;color:#718197;font-size:12px;line-height:1.6;">iBanking · Cổng thanh toán học phí<br>Đây là email tự động, vui lòng không trả lời email này.</td></tr>
</table></td></tr></table></body></html>"""


def otp_html(code: str, transaction_code: str) -> str:
    code, transaction_code = escape(code), escape(transaction_code)
    content = f"""<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#edf4ff;border:1px solid #dce9ff;border-radius:14px;"><tr><td align="center" style="padding:24px 16px;">
<div style="font-size:12px;font-weight:bold;color:#53677e;">MÃ XÁC THỰC</div><div style="margin-top:8px;font-size:34px;line-height:1.3;font-weight:bold;letter-spacing:8px;color:#235add;">{code}</div>
</td></tr></table>
<p style="margin:20px 0 8px;font-size:14px;line-height:1.6;color:#53677e;">Mã có hiệu lực trong <strong style="color:#122942;">5 phút</strong> và chỉ sử dụng một lần. Không chia sẻ mã này với bất kỳ ai.</p>
<p style="margin:0;font-size:13px;line-height:1.6;color:#718197;overflow-wrap:anywhere;word-break:break-all;">Mã giao dịch: {transaction_code}</p>"""
    return _layout(
        "XÁC THỰC GIAO DỊCH",
        "Mã OTP của bạn",
        "Nhập mã bên dưới để xác nhận thanh toán học phí.",
        content,
    )


def receipt_html(
    transaction_code: str,
    student_id: str,
    student_name: str,
    semester: str,
    amount: Decimal,
) -> str:
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if formatted.endswith(",00"):
        formatted = formatted[:-3]
    rows = [
        ("Mã giao dịch", transaction_code),
        ("Sinh viên", student_name),
        ("MSSV", student_id),
        ("Học kỳ", semester),
    ]
    details = "".join(
        f'<tr><td style="padding:10px 0;color:#718197;font-size:13px;vertical-align:top;">{escape(label)}</td>'
        f'<td align="right" style="padding:10px 0;color:#122942;font-size:13px;font-weight:bold;overflow-wrap:anywhere;word-break:break-word;">{escape(value)}</td></tr>'
        for label, value in rows
    )
    content = f"""<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#edf4ff;border:1px solid #dce9ff;border-radius:14px;"><tr><td style="padding:20px;">
<div style="font-size:12px;font-weight:bold;color:#53677e;">SỐ TIỀN ĐÃ THANH TOÁN</div><div style="margin-top:6px;color:#235add;font-size:27px;font-weight:bold;">{formatted} VND</div>
</td></tr></table>
<div style="margin:24px 0 4px;font-size:14px;font-weight:bold;color:#122942;">Chi tiết giao dịch</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="table-layout:fixed;">{details}</table>"""
    return _layout(
        "GIAO DỊCH THÀNH CÔNG",
        "Thanh toán hoàn tất",
        "Khoản học phí đã được thanh toán thành công. Thông tin giao dịch của bạn:",
        content,
    )

# iBanking – phân hệ thanh toán học phí

Python 3.10+. Năm tiến trình độc lập: Gateway/UI :8000, Auth–Account :8001, Payment :8002, Tuition :8003 và OTP/Email :8004. Gateway gọi các service qua HTTP; mỗi service dùng database riêng. Payment điều phối giao dịch; Account giữ số dư theo mã giao dịch; Tuition chỉ cho phép một lần chuyển khoản phí sang đã thanh toán.

## Chạy trên Windows / VS Code

Mở terminal tại thư mục dự án:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed_demo.py
.\.venv\Scripts\python.exe run_local.py
```

Mở http://127.0.0.1:8000. Dừng bằng Ctrl+C. Không cần kích hoạt virtual environment.

File `DB/connection string.txt` giữ tên database ở một dòng và URL PostgreSQL ở dòng kế tiếp: `auth_database`, `otp_database`, `tuition_database`, `payment_database`. Có thể thay bằng `AUTH_DATABASE_URL`, `OTP_DATABASE_URL`, `TUITION_DATABASE_URL` và `PAYMENT_DATABASE_URL`.

Schema phải được tạo sẵn bằng các file `DB/sql/`. Nếu database đã có schema cũ, chạy các migration trong `DB/migrations/` trên đúng database được ghi trong từng file. Script seed bổ sung dữ liệu thiếu, không reset số dư và không đổi mật khẩu hợp lệ đang có.

## Gmail API

OTP và email xác nhận dùng Gmail API `users.messages.send`. Tạo Google Cloud project, bật Gmail API, tạo OAuth client và lấy refresh token với scope `https://www.googleapis.com/auth/gmail.send`. Cấu hình các biến môi trường trong terminal trước khi chạy launcher:

```powershell
$env:GOOGLE_CLIENT_ID = "..."
$env:GOOGLE_CLIENT_SECRET = "..."
$env:GOOGLE_REFRESH_TOKEN = "..."
$env:GMAIL_SENDER = "your-sending-account@gmail.com"
```

Không lưu OAuth secrets trong source code hoặc Git. Khi chưa cấu hình, giao dịch vẫn được tạo ở trạng thái chờ OTP; có thể gửi lại OTP sau khi cấu hình Gmail.

## API nghiệp vụ

- `POST /api/auth/login`, `GET /api/account/info`
- `GET /api/tuition/{mssv}`
- `POST /api/payments` với `{ "tuition_fee_id": 1 }` để tạo giao dịch và gửi OTP
- `POST /api/payments/{transaction_code}/otp/resend` để gửi lại OTP
- `POST /api/payments/{transaction_code}/confirm` với `{ "code": "123456" }` để xác nhận
- `POST /api/payments/{transaction_code}/receipt/resend` để gửi lại biên nhận nếu thanh toán đã thành công nhưng email tạm lỗi
- `GET /api/payments/{transaction_code}` để xem trạng thái; `GET /api/account/transactions` để xem lịch sử

Các API nghiệp vụ cần bearer token từ bước đăng nhập. API nội bộ giữa services yêu cầu `X-Service-Token` và không được expose qua Gateway. Swagger: http://127.0.0.1:8001/docs, http://127.0.0.1:8002/docs, http://127.0.0.1:8003/docs và http://127.0.0.1:8004/docs.

Tài khoản demo mới: `alice`, `bob`, `charlie`; mật khẩu `Demo123!`. Email example.com là dữ liệu mẫu, cần đổi sang email nhận được trước khi kiểm tra OTP. Tra cứu `SV001`–`SV004`; SV004 đã thanh toán. JWT hết hạn sau một giờ; khởi động lại launcher làm mất hiệu lực phiên cũ. Chỉ chạy local; chưa cấu hình triển khai ra Internet.

# iBanking – bản thử đăng nhập và tra học phí

Python 3.10+. Ba tiến trình độc lập: Gateway/UI :8000, Auth–Account :8001 và Tuition :8003. Gateway gọi các service qua HTTP; mỗi service dùng database riêng. Chưa triển khai thanh toán, OTP hoặc email.

## Chạy trên Windows / VS Code

Mở terminal tại thư mục dự án:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed_demo.py
.\.venv\Scripts\python.exe run_local.py
```

Mở http://127.0.0.1:8000. Dừng bằng Ctrl+C. Không cần kích hoạt virtual environment.

File `DB/connection string.txt` giữ định dạng tên cấu hình ở một dòng và URL PostgreSQL ở dòng kế tiếp: `auth_database`, `otp_database`, `tuition_database`, `payment_database`. File này được Git bỏ qua. Có thể thay bằng biến môi trường `AUTH_DATABASE_URL` và `TUITION_DATABASE_URL`.

Schema phải được tạo sẵn trên database tương ứng bằng các file `DB/sql/`. Script seed bổ sung dữ liệu thiếu, không reset số dư và không đổi mật khẩu hợp lệ đang có; chỉ sửa hash placeholder ban đầu. Hai database seed trong hai transaction riêng; nếu kết nối thứ hai lỗi, có thể chạy lại script.

Tài khoản demo mới: `alice`, `bob`, `charlie`; mật khẩu `Demo123!`. Email example.com chỉ là dữ liệu mẫu. Tra cứu `SV001`–`SV004`; SV004 đã thanh toán. JWT hết hạn sau một giờ; khởi động lại launcher sẽ làm mất hiệu lực phiên cũ. Chỉ chạy local; chưa cấu hình triển khai ra Internet.

## Kiểm tra thủ công

1. Đăng nhập sai mật khẩu: phải báo lỗi; đăng nhập alice: hiện số dư và thông tin từ NeonDB.
2. Tra SV001: hiện học phí; SV004: đã thanh toán; mã không tồn tại: thông báo không tìm thấy.
3. Đăng xuất: không còn truy cập màn hình tài khoản. Gọi API tài khoản/tra cứu thiếu token: HTTP 401.
4. Chạy seed lần hai: không thêm trùng tài khoản/học phí và không reset số dư.

API service và Swagger: http://127.0.0.1:8001/docs và http://127.0.0.1:8003/docs.

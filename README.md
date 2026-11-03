# iBanking – bản thử đăng nhập và tra học phí

## Thanh toán với OTP placeholder

Đã thêm Payment Service :8004. Trước khi chạy bản này, dùng đúng Python đã cài dependencies:

```powershell
python migrate_payment.py
python run_local.py
```

Migration bổ sung bảng ghi nhận trừ/hoàn tiền và mã giao dịch gạch nợ, không reset dữ liệu. Trên UI, tra MSSV → Thanh toán → nhập OTP `123456` → Xác nhận. Đây là OTP cố định chỉ để thử luồng, chưa đáp ứng yêu cầu OTP/email của rubric. Launcher local bật `DEMO_OTP=1`; chạy Payment riêng mà không bật cờ này sẽ không xác nhận được. Thao tác thực sự cập nhật số dư và học phí trong database demo.

Nút xem giao dịch cho phép tiếp tục giao dịch đang chờ sau khi tải lại trang hoặc gián đoạn mạng. Giao dịch chờ OTP hết hiệu lực sau 5 phút; giao dịch đã bắt đầu xử lý được giữ lại để thử tiếp. Các thao tác trừ tiền, hoàn tiền và gạch nợ nhận mã giao dịch để tránh thực hiện lặp. Khôi phục hiện cần người dùng bấm tiếp tục; chưa có tác vụ tự động phục hồi. Nếu học phí đã được người khác trả, giao dịch sẽ hoàn tiền và có trạng thái `refunded`.

Thử với alice/SV001; sau thành công tra lại học phí, xem số dư và lịch sử. Thử OTP sai, thiếu số dư, xác nhận lại cùng giao dịch và hai tài khoản cùng trả một khoản. Không dùng lại khoản đã thanh toán để thử một lần thanh toán mới.

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

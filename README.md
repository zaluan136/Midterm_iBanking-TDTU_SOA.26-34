# iBanking · Thanh toán học phí

Đồ án giữa kỳ SOA: đăng nhập, tra cứu MSSV, thanh toán toàn bộ khoản học phí, xác thực OTP qua email và xem lịch sử giao dịch. Backend Python/FastAPI, dữ liệu PostgreSQL trên NeonDB, UI HTML/CSS/JavaScript.

## Kiến trúc

| Thành phần | Cổng local | Database sở hữu |
|---|---:|---|
| API Gateway + UI | 8000 | Không có |
| Auth–Account | 8001 | auth_database |
| Payment | 8002 | payment_database |
| Tuition | 8003 | tuition_database |
| OTP + email | 8004 | otp_database |

Có **4 service nghiệp vụ, 4 database và 1 Gateway**. Service giao tiếp qua HTTP với `X-Service-Token`; public API dùng JWT. Các ID liên database là liên kết logic; không tạo khóa ngoại giữa các database. Account giữ tiền theo mã giao dịch, Tuition gạch nợ có điều kiện, Payment điều phối commit/release và lưu trạng thái. Lỗi kết nối có thể tiếp tục qua cùng giao dịch; chưa có worker tự động khôi phục.

## 1. Cài đặt

Yêu cầu Python 3.10+ và 4 database PostgreSQL. Trong PowerShell tại thư mục dự án:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Các lệnh bên dưới dùng Python trong `.venv`, không cần kích hoạt môi trường.

## 2. Cấu hình database

Tạo file local `DB/connection string.txt` (Git bỏ qua), gồm tên cấu hình và URL tương ứng ở dòng kế tiếp:

```text
auth_database
postgresql://USER:PASSWORD@AUTH_HOST/neondb?sslmode=require

tuition_database
postgresql://USER:PASSWORD@TUITION_HOST/neondb?sslmode=require

payment_database
postgresql://USER:PASSWORD@PAYMENT_HOST/neondb?sslmode=require

otp_database
postgresql://USER:PASSWORD@OTP_HOST/neondb?sslmode=require
```

Dùng URL từ Neon của từng database. Có thể thay bằng biến môi trường `AUTH_DATABASE_URL`, `TUITION_DATABASE_URL`, `PAYMENT_DATABASE_URL`, `OTP_DATABASE_URL`.

- Database mới: chạy từng file trong `DB/sql/` trên đúng database tương ứng, rồi seed.
- Database đã dùng bản cũ: chạy migration dưới đây; không chạy lại `CREATE TABLE` của schema mới.

```powershell
.\.venv\Scripts\python.exe apply_schema_updates.py
.\.venv\Scripts\python.exe seed_demo.py
```

Migration giữ dữ liệu, thêm bảng/cột cần thiết và bỏ các khóa ngoại cũ đặt sai database. Mỗi database dùng một transaction riêng; nếu một bước lỗi, sửa nguyên nhân rồi chạy lại. Seed bổ sung tài khoản/học phí thiếu và sửa hash placeholder, không reset số dư hay mật khẩu hợp lệ đang có.

Tài khoản mẫu: `alice`, `bob`, `charlie`; mật khẩu mới mặc định `Demo123!`. MSSV: `SV001`–`SV004`. Email `example.com` là dữ liệu mẫu: đổi sang email nhận được thư bằng Công cụ demo.

## 3. Thiết lập Gmail gửi OTP

1. Trong Google Cloud, tạo project và bật Gmail API.
2. Google Auth Platform: cấu hình ứng dụng External/Testing và thêm Gmail gửi thư vào Test users.
3. Tạo OAuth Client loại Desktop app, tải `client_secret_*.json` vào thư mục gốc dự án.
4. Chạy lệnh dưới, chọn đúng Gmail gửi thư và cấp quyền `gmail.send` trên trình duyệt:

```powershell
.\.venv\Scripts\python.exe setup_gmail.py
```

Nhập lại đúng Gmail vừa cấp quyền. Script lưu `.env.gmail` ngoài Git; OTP Service tự đọc file này. Các biến sử dụng: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GMAIL_SENDER`. Không commit file OAuth hoặc token. Khi app còn Testing, token có thể hết hạn sau 7 ngày; nếu cần cấp quyền lại, đổi tên file `.env.gmail` cũ rồi chạy setup lần nữa. Thư demo có thể nằm trong Spam.

## 4. Khởi chạy và sử dụng

```powershell
.\.venv\Scripts\python.exe run_local.py
```

Mở **http://127.0.0.1:8000/**. Các cổng 8001–8004 phục vụ API, không có trang chủ. Ctrl+C dừng toàn bộ tiến trình. Sau khi đổi code/config, khởi động lại và Ctrl+F5 trình duyệt.

Đăng nhập → tra MSSV → chọn khoản chưa trả → xác nhận toàn bộ số tiền → nhập OTP trong email → xem kết quả và lịch sử. Nếu gửi OTP lỗi, dùng Gửi lại OTP trên cùng giao dịch. Nếu phản hồi bị chậm, kiểm tra lại trạng thái giao dịch trước khi tạo giao dịch mới. Giao dịch success đã trừ số dư và gạch nợ; lỗi gửi biên nhận không đảo ngược thanh toán.

## Công cụ demo

Nút **Công cụ demo** nằm trên thanh đầu trang sau khi đăng nhập.

- Chọn tài khoản trong danh sách để sửa username, họ tên, email, điện thoại, mật khẩu và số dư. Sửa theo ID nên đổi username vẫn giữ lịch sử. Để trống mật khẩu khi muốn giữ mật khẩu cũ.
- Chọn Tạo mới để thêm tài khoản. Username không được trùng; tài khoản mới cần mật khẩu.
- Thêm khoản học phí theo MSSV, tên sinh viên, học kỳ và số tiền; mỗi lần lưu tạo một khoản chưa thanh toán mới.
- Chặn sửa tài khoản khi còn khoản giữ tiền chưa hoàn tất.

Đây là công cụ chuẩn bị dữ liệu **local**, không phải phân quyền admin production. Mọi tài khoản đã đăng nhập đều có thể dùng khi `DEMO_ADMIN=1`; dữ liệu được ghi thật vào NeonDB. Launcher mặc định bật demo. Để tắt:

```powershell
$env:DEMO_ADMIN='0'
.\.venv\Scripts\python.exe run_local.py
```

Chỉ dùng bản này local. JWT và các khóa service tự tạo mỗi lần khởi động nếu chưa cấu hình; đặt `JWT_SECRET`, `SERVICE_TOKEN`, `OTP_SECRET` ổn định nếu muốn giữ phiên/OTP qua lần khởi động lại.

## API chính

| Method | URI | Chức năng |
|---|---|---|
| POST | /api/auth/login | Đăng nhập |
| GET | /api/account/info | Thông tin và số dư |
| GET | /api/tuition/{mssv} | Tra cứu học phí |
| POST | /api/payments | Tạo giao dịch, yêu cầu gửi OTP |
| POST | /api/payments/{code}/otp/resend | Gửi lại OTP |
| POST | /api/payments/{code}/confirm | Xác nhận với body `{"code":"mã OTP thực"}` |
| GET | /api/payments/{code} | Chi tiết/trạng thái |
| GET | /api/account/transactions | Lịch sử |
| POST | /api/payments/{code}/receipt/resend | Gửi biên nhận nếu chưa gửi |

Swagger của từng service: `http://127.0.0.1:<port>/docs`. Public API trừ login yêu cầu Bearer JWT. Các endpoint `/api/demo/*` chỉ bật trong chế độ demo và yêu cầu đăng nhập.

## Kiểm tra trước buổi demo

Kiểm tra một giao dịch thành công, OTP sai/hết hạn, không đủ số dư, khoản đã trả, xác nhận lặp và tiếp tục giao dịch sau gián đoạn. Đối chiếu số dư, trạng thái học phí và lịch sử. Hai tình huống concurrency cần demo riêng: nhiều giao dịch dùng cùng số dư và nhiều tài khoản cùng trả một khoản học phí. Code có cơ chế xử lý nhưng chưa có báo cáo kiểm thử concurrency kèm bản này.

## Các file được giữ ngoài Git

Connection string, `.env*`, OAuth JSON/token, `.venv*`, `__pycache__`, file test/chẩn đoán và script cũ. App đọc cấu hình từ `services/config.py`, không phụ thuộc file test. Schema/migration, setup Gmail và seed được giữ lại để thành viên khác chạy được.

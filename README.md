# iBanking - Thanh toán học phí

Ứng dụng iBanking hỗ trợ tra cứu và thanh toán học phí trực tuyến. Người dùng xác nhận giao dịch bằng OTP qua email, sau đó theo dõi kết quả và lịch sử thanh toán.

Đồ án giữa kỳ môn **Service-Oriented Architecture** được xây dựng với FastAPI, PostgreSQL và giao diện HTML, CSS, JavaScript.

## Chức năng

- Đăng nhập, xem thông tin tài khoản và số dư.
- Tra cứu học phí theo mã số sinh viên; thanh toán toàn bộ một khoản chưa trả.
- Xác nhận giao dịch bằng OTP qua email, có hiệu lực 5 phút và chỉ dùng một lần.
- Xem trạng thái, lịch sử giao dịch và nhận biên nhận qua email.
- Bảo vệ số dư và học phí khi nhiều giao dịch được xử lý đồng thời.
- Chuẩn bị dữ liệu thử bằng công cụ demo.

## Kiến trúc

| Thành phần            | Cổng local | Trách nhiệm                                        |
| --------------------- | ---------: | -------------------------------------------------- |
| API Gateway và Web UI |       8000 | Cung cấp giao diện và chuyển tiếp public API.      |
| Auth–Account          |       8001 | Xác thực, tài khoản, số dư và giữ tiền.            |
| Payment               |       8002 | Tạo, điều phối và lưu giao dịch.                   |
| Tuition               |       8003 | Tra cứu học phí và cập nhật trạng thái thanh toán. |
| OTP và Email          |       8004 | Tạo, xác thực OTP và gửi email qua Gmail API.      |

Có **4 service nghiệp vụ, 4 database và 1 Gateway**. Service giao tiếp qua HTTP với `X-Service-Token`; public API dùng JWT. Các ID liên database là liên kết logic, không phải khóa ngoại giữa các database.

Sau khi OTP hợp lệ, Payment yêu cầu Auth–Account giữ tiền, Tuition đánh dấu khoản phí đã trả và Auth–Account hoàn tất khoản giữ. Nếu khoản phí đã được giao dịch khác thanh toán, Payment yêu cầu giải phóng tiền. Payment thử khôi phục các giao dịch đang xử lý sau gián đoạn. Đây là cơ chế nhất quán cuối cùng giữa các database, không phải một transaction ACID chung.

## Cài đặt và cấu hình

### 1. Cài thư viện

Yêu cầu Python 3.10+ và 4 database PostgreSQL. Trong PowerShell tại thư mục dự án:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Các lệnh bên dưới dùng Python trong `.venv`, không cần kích hoạt môi trường.

### 2. Cấu hình database

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
Mặc định ứng dụng dùng schema `public`; nếu toàn bộ các bảng nằm trong schema khác, đặt biến môi trường `DB_SCHEMA` tương ứng.

- Database mới: chạy từng file trong `DB/sql/` trên đúng database tương ứng, rồi seed.
- Database đã dùng bản cũ: chạy migration dưới đây; không chạy lại `CREATE TABLE` của schema mới.

```powershell
.\.venv\Scripts\python.exe apply_schema_updates.py
.\.venv\Scripts\python.exe seed_demo.py
```

Migration giữ dữ liệu, thêm bảng/cột cần thiết và bỏ các khóa ngoại cũ đặt sai database. Mỗi database dùng một transaction riêng; nếu một bước lỗi, sửa nguyên nhân rồi chạy lại. Seed bổ sung tài khoản/học phí thiếu và sửa hash placeholder, không reset số dư hay mật khẩu hợp lệ đang có.

Tài khoản mẫu: `alice`, `bob`, `charlie`; mật khẩu mới mặc định `Demo123!`. MSSV: `SV001`–`SV004`. Email `example.com` là dữ liệu mẫu: đổi sang email nhận được thư bằng Công cụ demo.

### 3. Thiết lập Gmail gửi OTP

1. Trong Google Cloud, tạo project và bật Gmail API.
2. Google Auth Platform: cấu hình ứng dụng External/Testing và thêm Gmail gửi thư vào Test users.
3. Tạo OAuth Client loại Desktop app, tải `client_secret_*.json` vào thư mục gốc dự án.
4. Chạy lệnh dưới, chọn đúng Gmail gửi thư và cấp quyền `gmail.send` trên trình duyệt:

```powershell
.\.venv\Scripts\python.exe setup_gmail.py
```

Nhập lại đúng Gmail vừa cấp quyền. Script lưu `.env.gmail` ngoài Git; OTP Service tự đọc file này. Các biến sử dụng: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GMAIL_SENDER`. Không commit file OAuth hoặc token. Khi app còn Testing, token có thể hết hạn sau 7 ngày; nếu cần cấp quyền lại, đổi tên file `.env.gmail` cũ rồi chạy setup lần nữa. Thư demo có thể nằm trong Spam.

## Khởi chạy và sử dụng

```powershell
.\.venv\Scripts\python.exe run_local.py
```

Mở **http://127.0.0.1:8000/**. Các cổng 8001–8004 phục vụ API, không có trang chủ. Ctrl+C dừng toàn bộ tiến trình. Sau khi đổi code/config, khởi động lại và Ctrl+F5 trình duyệt.

1. Đăng nhập và xem số dư trong mục **Tài khoản**.
2. Nhập mã số sinh viên và chọn một khoản học phí chưa thanh toán.
3. Kiểm tra thông tin, điều khoản và xác nhận để nhận OTP.
4. Nhập OTP trong email để hoàn tất thanh toán.
5. Kiểm tra số dư, trạng thái học phí, lịch sử và biên nhận.

Nếu gửi OTP lỗi, dùng **Gửi lại OTP** trên cùng giao dịch. Nếu phản hồi bị chậm, kiểm tra trạng thái trước khi tạo giao dịch mới. Gửi biên nhận lỗi không đảo ngược giao dịch đã thành công.

Tra cứu tự chạy khi ngừng nhập MSSV trong khoảng nửa giây. Sau khi khởi động lại, giữ các service chạy để Payment tự thử khôi phục giao dịch đã xác thực OTP. Cơ chế khóa trong tiến trình dành cho một instance Payment như launcher local; chưa hỗ trợ nhiều instance Payment cùng lúc.

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

Các endpoint hiện hành được liệt kê dưới đây. File `DB/API Specification – iBanking Midterm.pdf` mô tả thiết kế cũ, không khớp hoàn toàn với code.

| Method | URI                                 | Chức năng                                  |
| ------ | ----------------------------------- | ------------------------------------------ |
| POST   | /api/auth/login                     | Đăng nhập                                  |
| GET    | /api/account/info                   | c Thông tin và số dư                       |
| GET    | /api/tuition/{mssv}                 | Tra cứu học phí                            |
| POST   | /api/payments                       | Tạo giao dịch, yêu cầu gửi OTP             |
| POST   | /api/payments/{code}/otp/resend     | Gửi lại OTP                                |
| POST   | /api/payments/{code}/confirm        | Xác nhận với body `{"code":"mã OTP thực"}` |
| GET    | /api/payments/{code}                | Chi tiết/trạng thái                        |
| GET    | /api/account/transactions           | Lịch sử                                    |
| POST   | /api/payments/{code}/receipt/resend | Gửi lại biên nhận của giao dịch thành công |

Khi chạy Python local, xem Swagger của từng service tại `http://127.0.0.1:<port>/docs`. Với Docker Compose, chỉ Gateway được mở ra máy host tại cổng 8000. Public API trừ login yêu cầu Bearer JWT. Các endpoint `/api/demo/*` chỉ bật trong chế độ demo và yêu cầu đăng nhập.

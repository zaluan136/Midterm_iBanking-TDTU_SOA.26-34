# Hai phương án demo ĐỘC LẬP

Chỉ chọn một cách tại một thời điểm. Cả hai dùng cùng NeonDB và Gmail đang có, nên vẫn phụ thuộc mạng/Neon/Gmail. Chúng chỉ dự phòng cho lỗi của cách chạy app hoặc chia sẻ web, không dự phòng khi DB/Gmail cùng lỗi.

## A. Docker local — không dùng ngrok

Mở Docker Desktop (Linux containers), tại IBanking_2:

```powershell
.\start_docker.cmd
```

Script tự tạo .env.docker nếu thiếu, build/chạy 5 app container, đợi healthy và in http://127.0.0.1:8000/. Công cụ demo bật. Không cần tài khoản, token hoặc CLI ngrok. Ctrl+C tự stop container; không cần lệnh up/down.

`start_demo.cmd` cũ hiện là alias cho cách A. `--local` cũng chỉ chạy Docker. Không còn chế độ Docker + ngrok.

## B. App Python local + ngrok — không dùng Docker

Cài ngrok CLI từ https://ngrok.com/download/windows nếu chưa có, mở lại terminal để nhận PATH. Dùng .venv và thư viện Python của dự án như khi chạy run_local.py.

```powershell
.\start_ngrok.cmd
```

Script tự chạy 5 tiến trình Python/Uvicorn, sau đó mở ngrok trỏ Gateway local và in link HTTPS. Không gọi Docker; Docker Desktop có thể đóng. Công cụ demo bị tắt khi chia sẻ public.

Lần đầu script đọc token từ biến NGROK_AUTHTOKEN hoặc cấu hình ngrok có sẵn; nếu chưa có thì hỏi Authtoken (ký tự ẩn), lưu .env.ngrok cho các lần sau. Lấy token tại https://dashboard.ngrok.com/get-started/your-authtoken. Token ngrok khác cấu hình Gmail. Không cần chạy run_local.py trước: launcher tự chạy app.

Ctrl+C dừng cả app và ngrok. Máy cần bật và có Internet khi chia sẻ link. Free ngrok có thể hiện trang xác nhận truy cập trước khi mở app.

## Chuyển phương án

Đang Docker lỗi/không muốn dùng: Ctrl+C ở terminal Docker, chờ dừng rồi chạy start_ngrok.cmd. Đang ngrok lỗi: Ctrl+C, mở Docker Desktop rồi chạy start_docker.cmd. Không chạy hai script đồng thời vì cùng cổng 8000. Script sẽ báo lỗi nếu cổng đang bị giữ thay vì tự kill ứng dụng khác.

Nếu chỉ cần demo local mà cả Docker/ngrok đều không dùng được, vẫn có `python run_local.py` và mở http://127.0.0.1:8000/.

## Cấu hình và kiểm tra

Cả hai cách dùng `.env.gmail` và `DB/connection string.txt`. Không dùng run_render.py. Docker giữ khóa ổn định trong .env.docker; nhánh Python/ngrok tạo khóa phiên mới khi chạy nếu chưa có các biến khóa trên máy. Sau restart Python cần login lại và xin OTP mới cho giao dịch chưa xác thực.

Chưa build/chạy thực tế Docker/ngrok trong phiên sửa vì máy chưa tìm thấy hai CLI. Kiểm tra launcher dùng tiến trình giả để xác nhận mỗi nhánh chỉ gọi đúng công cụ của nó, dọn tiến trình khi lỗi và Ctrl+C; không gửi Gmail hay sửa DB trong kiểm tra đó.

Để commit bản tách hai phương án:

```powershell
git add -A -- run_demo.py start_demo.cmd start_docker.cmd start_ngrok.cmd ngrok-native.yml compose.ngrok.yaml ngrok-demo.yml README.md Presentation/DOCKER.md Presentation/DOCKER-NGROK.md
git commit -m "Separate Docker local and native ngrok demo modes"
git push origin main
```

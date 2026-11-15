# Docker + ngrok bằng một lệnh

Mở Docker Desktop, dùng Linux containers. Tại IBanking_2 chạy:

```powershell
.\start_demo.cmd
```

Script tự tạo .env.docker (khóa ổn định), build app, chạy Gateway + 4 service + ngrok, đợi API sẵn sàng rồi in LOCAL và PUBLIC URL. Ngrok chạy bằng image chính thức, không cần cài ngrok riêng. Ctrl+C tự stop project; container/image được giữ cho lần sau, không xóa dữ liệu Neon. Đừng đóng cưỡng bức terminal nếu muốn script dọn phiên đúng cách.

Một lần đầu: tạo tài khoản ngrok nếu chưa có, lấy Authtoken tại https://dashboard.ngrok.com/get-started/your-authtoken, dán khi script hỏi (ký tự được ẩn). Script ưu tiên token từ NGROK_AUTHTOKEN hoặc file cấu hình ngrok có sẵn rồi mới hỏi. Token lưu trong .env.ngrok, được .gitignore bỏ qua. Không phải API key Gmail và không phải ngrok API key.

App dùng nguyên .env.gmail và DB/connection string.txt đang có. Không cần run_render.py. Dừng run_local.py trước vì dùng cùng cổng 8000. Máy cần Internet và phải bật Docker trong suốt buổi demo. Free ngrok có thể hiện trang xác nhận truy cập trước khi vào app.

## Chỉ chạy local để chuẩn bị dữ liệu

```powershell
.\start_demo.cmd --local
```

Chế độ này chỉ chạy 5 app container, bật Công cụ demo. Chế độ mặc định có public URL tắt Công cụ demo để người truy cập không thay số dư/tài khoản. Chuẩn bị dữ liệu khi local rồi Ctrl+C, sau đó chạy lệnh mặc định để chia sẻ link.

## Điều kiện trước lần đầu

- Docker Desktop đã cài và engine đang chạy. Script không tự cài Docker hoặc bật WSL.
- Có Python; dùng .venv hiện có hoặc Python trên máy. run_demo.py chỉ dùng thư viện chuẩn, không cần pip install cho launcher.
- Có .env.gmail còn quyền gửi thư và DB/connection string.txt đủ 4 kết nối.
- Có ngrok authtoken. Nếu ngrok báo tài khoản cần xác minh, thực hiện theo dashboard chính thức.

Nếu cổng 8000/4040 bận: dừng app/ngrok hoặc phiên demo cũ. Nếu container chưa healthy: xem log script in ra; nếu Gmail invalid_grant: cấp quyền lại local rồi chạy lại demo. Nếu DB chưa khởi tạo/migration thì xử lý theo README; script không tự sửa/seed DB khi khởi động.

Nếu đóng terminal cưỡng bức và container còn chạy: mở Docker Desktop, stop project ibanking, rồi chạy lại script. Đây là demo trên máy cá nhân có tunnel, không phải hosting hoạt động sau khi tắt máy.

## Git: chỉ phần Docker/ngrok

```powershell
git add Dockerfile .dockerignore compose.yaml compose.ngrok.yaml ngrok-demo.yml run_demo.py start_demo.cmd services/gateway.py Presentation/DOCKER.md Presentation/DOCKER-NGROK.md
git commit -m "Add one-command Docker and ngrok demo"
git push origin main
```

Không dùng git add . nếu đang bỏ qua phần Render và các thay đổi khác.

## Trạng thái kiểm tra

Launcher có kiểm tra tự động bằng mô phỏng, không gọi Neon/Gmail. Cần Docker Desktop để build và thử container thực tế. Máy trong phiên chuẩn bị chưa tìm thấy Docker CLI nên chưa xác nhận chạy toàn bộ Docker/ngrok.

Tài liệu chính thức: https://ngrok.com/download/docker ; https://ngrok.com/docs/gateway/agent/config/v3 ; https://docs.docker.com/reference/cli/docker/compose/up/

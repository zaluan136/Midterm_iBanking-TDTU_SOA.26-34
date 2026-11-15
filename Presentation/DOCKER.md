> Chạy Docker local bằng một lệnh: `.\start_docker.cmd`. Docker không chạy ngrok. Phương án ngrok độc lập dùng `.\start_ngrok.cmd`; xem [DOCKER-NGROK.md](DOCKER-NGROK.md).

# Chạy iBanking bằng Docker Compose

Yêu cầu Docker Desktop đang chạy Linux containers, Docker Compose v2; vẫn dùng 4 database Neon. Cấu hình Gmail nằm trong .env.gmail; OAuth phải còn hiệu lực. Không cần đăng nhập Google bên trong container.

## Chuẩn bị

Trong terminal của IBanking_2:

```powershell
.\.venv\Scripts\python.exe setup_docker.py
docker compose config --quiet
docker compose build
```

Kiểm tra đã có `DB/connection string.txt` và `.env.gmail`. `setup_docker.py` sinh .env.docker với khóa chung ổn định, không ghi đè file cũ. Không commit file .env.docker. Dừng launcher local trước khi bật Docker vì cùng cổng 8000.

## Chạy

```powershell
docker compose up -d
docker compose ps
docker compose logs --tail 60 gateway payment otp
```

Mở http://127.0.0.1:8000/. Chỉ Gateway mở cổng ra máy; các service khác giao tiếp bằng tên container. Mỗi container dùng cổng nội bộ 8000, khác các cổng launcher local. Healthcheck xác nhận API sống, không chứng minh Neon/Gmail hoạt động; vẫn thử một giao dịch thật.

Database đã có dữ liệu thì không cần seed lại. Nếu cần nâng schema cũ hoặc bổ sung dữ liệu mẫu:

```powershell
docker compose run --rm --no-deps gateway python apply_schema_updates.py
docker compose run --rm --no-deps gateway python seed_demo.py
```

Hai lệnh trên thay đổi DB đã cấu hình. Database hoàn toàn mới cần khởi tạo schema theo README gốc trước.

## Test hai ca đồng thời

```powershell
docker compose --profile test run --rm --no-deps tests
```

Chạy test tích hợp bằng schema tạm trên Neon, mail giả. Không cần bật các container API để chạy test này. Cần cả hai dòng PASS concurrent... và không có traceback. Test không đo tải hay chứng minh triển khai nhiều Payment instance.

## Dừng và cập nhật

```powershell
docker compose down
docker compose up -d --build
```

Sau cấp quyền Gmail mới: `docker compose up -d --force-recreate otp`. Container phải được tạo lại để đọc env_file mới. Đừng scale Payment nhiều instance: khóa điều phối hiện nằm trong tiến trình.

## Trạng thái kiểm chứng

Cấu hình được chuẩn bị theo code hiện tại. Máy trong phiên chuẩn bị chưa có lệnh Docker nên chưa build/chạy container thực tế. Phải chạy `docker compose config --quiet`, build và demo Gmail trên máy có Docker Desktop trước khi báo cáo đã triển khai thành công.

Tham khảo: https://docs.docker.com/compose/how-tos/startup-order/ và https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/

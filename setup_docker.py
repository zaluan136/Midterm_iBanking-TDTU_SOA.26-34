"""Create local shared service keys without replacing existing keys."""
from pathlib import Path
import secrets

if __name__ == "__main__":
    target = Path(__file__).resolve().parent / ".env.docker"
    try:
        with target.open("x", encoding="utf-8") as f:
            for name in ("JWT_SECRET", "SERVICE_TOKEN", "OTP_SECRET"):
                f.write(f"{name}={secrets.token_urlsafe(48)}\n")
            f.write("DEMO_ADMIN=1\nDB_SCHEMA=public\n")
        print("Đã tạo .env.docker. Giữ file này để khóa không đổi sau restart.")
    except FileExistsError:
        print("Đã có .env.docker; giữ cấu hình hiện tại.")

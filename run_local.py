"""Run the gateway and all iBanking services; Ctrl+C stops them."""
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

if __name__ == '__main__':
    env = os.environ.copy()
    env.setdefault('JWT_SECRET', secrets.token_urlsafe(48))
    env.setdefault('SERVICE_TOKEN', secrets.token_urlsafe(48))
    env.setdefault('OTP_SECRET', secrets.token_urlsafe(48))
    processes = []
    try:
        for name, port in [('auth_account', 8001), ('tuition', 8003), ('otp', 8004), ('payment', 8002), ('gateway', 8000)]:
            processes.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', f'services.{name}:app', '--host', '127.0.0.1', '--port', str(port)], env=env, cwd=Path(__file__).resolve().parent))
        print('Mở http://127.0.0.1:8000 — Ctrl+C để dừng.', flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

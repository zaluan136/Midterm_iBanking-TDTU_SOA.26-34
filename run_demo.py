"""Run the Docker demo locally."""

import argparse
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def compose_command():
    return ["docker", "compose", "-f", "compose.yaml"]


def run(command, env, **kwargs):
    return subprocess.run(command, cwd=ROOT, env=env, check=True, **kwargs)


def prepare_keys():
    target = ROOT / ".env.docker"
    if not target.exists():
        with target.open("x", encoding="utf-8") as f:
            for name in ("JWT_SECRET", "SERVICE_TOKEN", "OTP_SECRET"):
                f.write(f"{name}={secrets.token_urlsafe(48)}\n")
            f.write("DB_SCHEMA=public\n")


def ensure_port_free(port):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(
                f"Cong {port} dang duoc dung. Dung app local hoac phien demo cu truoc khi chay."
            )


def docker_mode():
    env = os.environ.copy()
    env["DEMO_ADMIN"] = "1"
    command = compose_command()
    attempted = False
    try:
        if not shutil.which("docker"):
            raise RuntimeError(
                "Chua co Docker Desktop. Cai Docker Desktop, mo ung dung (Linux containers), roi chay lai lenh nay."
            )
        run(["docker", "compose", "version"], env, stdout=subprocess.DEVNULL)
        run(
            ["docker", "info"],
            env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for relative in ("databases/connection string.txt", ".env.gmail"):
            if not (ROOT / relative).is_file():
                raise RuntimeError("Thieu file: " + relative)
        ensure_port_free(8000)
        prepare_keys()
        run(command + ["config", "--quiet"], env)
        print(
            "Dang build va khoi dong Docker; lan dau can tai image va thu vien...",
            flush=True,
        )
        attempted = True
        run(command + ["up", "--build", "-d", "--wait", "--wait-timeout", "180"], env)
        print("\nLOCAL: http://127.0.0.1:8000/", flush=True)
        print("Docker local. Cong cu demo da bat.", flush=True)
        print("Nhan Ctrl+C de dung Docker. Khong can go lenh down.", flush=True)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDang dung demo...", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print("\nKhong khoi dong duoc: " + str(exc), file=sys.stderr, flush=True)
        if attempted:
            subprocess.run(
                command + ["logs", "--tail", "25"], cwd=ROOT, env=env, check=False
            )
        return 1
    finally:
        if attempted:
            try:
                subprocess.run(
                    command + ["stop", "--timeout", "15"],
                    cwd=ROOT,
                    env=env,
                    check=False,
                )
            except OSError:
                print(
                    "Khong goi duoc Docker de dung. Mo Docker Desktop va dung project ibanking.",
                    file=sys.stderr,
                )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--local", action="store_true", help="Alias for Docker local, the default"
    )
    modes.add_argument("--docker", action="store_true", help="Docker local")
    parser.parse_args(argv)
    return docker_mode()


if __name__ == "__main__":
    sys.exit(main())

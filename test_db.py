"""Read-only connection and schema check for the four iBanking Neon databases."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
CONNECTION_FILE = ROOT / "DB" / "connection string.txt"
EXPECTED_TABLES = {
    "auth_database": "app_user",
    "otp_database": "otp",
    "tuition_database": "tuition_fee",
    "payment_database": "payment_transaction",
}


def connection_hint(exc: Exception) -> str:
    """Return a useful diagnosis without printing credentials or host names."""
    message = str(exc).lower()
    if "could not translate host name" in message or "name or service not known" in message:
        return "không phân giải được hostname; kiểm tra lại URL trong Neon Console"
    if "password authentication failed" in message:
        return "sai thông tin đăng nhập; sao chép lại connection string"
    if "does not exist" in message and "database" in message:
        return "database không tồn tại; kiểm tra tên database trong URL"
    if "timeout" in message or "timed out" in message:
        return "hết thời gian kết nối; kiểm tra mạng hoặc thử lại"
    if "connection refused" in message:
        return "server từ chối kết nối; kiểm tra endpoint và trạng thái Neon"
    return "kiểm tra URL, mạng và quyền truy cập"


def load_connections(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"Không tìm thấy file kết nối: {path}")

    connections: dict[str, str] = {}
    current_name: str | None = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if value in EXPECTED_TABLES:
            current_name = value
        elif value.startswith(("postgresql://", "postgres://")) and current_name:
            connections[current_name] = value
            current_name = None

    missing = set(EXPECTED_TABLES) - connections.keys()
    if missing:
        raise ValueError("Thiếu connection string cho: " + ", ".join(sorted(missing)))
    return connections


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--connection-file", type=Path, default=CONNECTION_FILE,
        help="File chứa tên database và URL kết nối; mặc định là DB/connection string.txt",
    )
    args = parser.parse_args()

    try:
        import psycopg
    except ImportError:
        print('Thiếu thư viện psycopg. Cài bằng: py -m pip install "psycopg[binary]"', file=sys.stderr)
        return 2

    try:
        connections = load_connections(args.connection_file)
    except (OSError, ValueError) as exc:
        print(f"Lỗi cấu hình: {exc}", file=sys.stderr)
        return 2

    failed = False
    for name, table in EXPECTED_TABLES.items():
        try:
            # A read-only transaction prevents this diagnostic from changing data.
            with psycopg.connect(connections[name], connect_timeout=10) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SELECT current_database(), to_regclass(%s)", (f"public.{table}",))
                    database, found_table = cur.fetchone()
                    if found_table is None:
                        print(f"[THIẾU BẢNG] {name}: kết nối OK ({database}), thiếu public.{table}")
                        failed = True
                    else:
                        # Table names are fixed constants above, never user input.
                        from psycopg import sql
                        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier("public", table)))
                        count = cur.fetchone()[0]
                        print(f"[OK] {name}: {database} | {table}: {count} dòng")
        except psycopg.Error as exc:
            # Do not print the exception: drivers may include connection details.
            print(f"[LỖI] {name}: {exc.__class__.__name__} ({connection_hint(exc)})")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Database connection settings shared by services and setup scripts."""

from pathlib import Path

CONNECTION_FILE = (
    Path(__file__).resolve().parents[1] / "databases" / "connection string.txt"
)


def load_connections(path=CONNECTION_FILE):
    names = {"auth_database", "tuition_database", "payment_database", "otp_database"}
    connections = {}
    current = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        value = line.strip()
        if value in names:
            current = value
        elif current and value.startswith(("postgresql://", "postgres://")):
            connections[current] = value
            current = None
    missing = names - connections.keys()
    if missing:
        raise ValueError("Missing database settings: " + ", ".join(sorted(missing)))
    return connections

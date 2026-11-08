import os
import hmac
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import Lock

import jwt
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from services.config import load_connections, CONNECTION_FILE

logger = logging.getLogger('ibanking.database')
_pools = {}
_pools_lock = Lock()


@contextmanager
def database(name):
    with _pools_lock:
        pool = _pools.get(name)
        if pool is None:
            url = os.getenv(name.upper() + '_URL') or load_connections(CONNECTION_FILE)[name]
            pool = ConnectionPool(
                url, min_size=0, max_size=5, timeout=10,
                kwargs={'connect_timeout': 10, 'row_factory': dict_row},
                check=ConnectionPool.check_connection, open=True,
            )
            _pools[name] = pool
    try:
        with pool.connection() as conn:
            # A transaction pooler can reuse a server session with a stale
            # search_path. Keep this setting scoped to the current transaction.
            conn.execute(sql.SQL('SET LOCAL search_path TO {}').format(
                sql.Identifier(os.environ.get('DB_SCHEMA', 'public')),
            ))
            yield conn
    except PoolTimeout as exc:
        raise psycopg.OperationalError('Database connection unavailable') from exc


def close_database_pools():
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()


def secret():
    value = os.environ.get('JWT_SECRET')
    if not value:
        raise RuntimeError('Khởi chạy bằng py run_local.py hoặc đặt JWT_SECRET.')
    return value


def token_for(user_id):
    return jwt.encode({'sub': str(user_id), 'exp': datetime.now(timezone.utc) + timedelta(hours=1)}, secret(), algorithm='HS256')


def current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    if not credentials:
        raise HTTPException(401, 'Vui lòng đăng nhập')
    try:
        payload = jwt.decode(credentials.credentials, secret(), algorithms=['HS256'], options={'require': ['exp', 'sub']})
        return int(payload['sub'])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(401, 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn')


def require_service_token(token: str | None = Header(default=None, alias='X-Service-Token')):
    expected = os.environ.get('SERVICE_TOKEN')
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(401, 'Service authentication required')


def make_app(title):
    app = FastAPI(title=title)

    app.on_event('shutdown')(close_database_pools)

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        diag = getattr(exc, 'diag', None)
        logger.error('Database error on %s %s: type=%s sqlstate=%s table=%s column=%s constraint=%s',
                     request.method, request.url.path, type(exc).__name__,
                     getattr(exc, 'sqlstate', None), getattr(diag, 'table_name', None),
                     getattr(diag, 'column_name', None), getattr(diag, 'constraint_name', None))
        return JSONResponse(status_code=503, content={'detail': 'Không truy cập được database. Kiểm tra cấu hình kết nối.'})

    @app.get('/health')
    def health():
        return {'status': 'ok'}
    return app

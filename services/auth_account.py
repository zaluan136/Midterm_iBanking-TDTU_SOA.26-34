import bcrypt
from decimal import Decimal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from services.common import (
    make_app,
    database,
    token_for,
    current_user,
    require_service_token,
)

app = make_app("iBanking Auth–Account")
from services.demo_admin import attach_accounts

attach_accounts(app)


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)


class Reservation(BaseModel):
    transaction_code: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


@app.post("/api/auth/login")
def login(body: Login):
    with database("auth_database") as conn:
        user = conn.execute(
            "SELECT id, full_name, password_hash FROM app_user WHERE username = %s",
            (body.username,),
        ).fetchone()
    valid = False
    if user and len(body.password.encode()) <= 72:
        try:
            valid = bcrypt.checkpw(
                body.password.encode(), user["password_hash"].encode()
            )
        except ValueError:
            pass
    if not valid:
        raise HTTPException(401, "Sai username hoặc password")
    return {
        "token": token_for(user["id"]),
        "user_id": user["id"],
        "full_name": user["full_name"],
    }


@app.get("/api/account/info")
def account(user_id: int = Depends(current_user)):
    with database("auth_database") as conn:
        user = conn.execute(
            "SELECT id, full_name, phone, email, balance FROM app_user WHERE id = %s",
            (user_id,),
        ).fetchone()
    if not user:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    user["balance"] = str(user["balance"])
    return user


@app.get("/internal/accounts/{user_id}", dependencies=[Depends(require_service_token)])
def internal_account(user_id: int):
    with database("auth_database") as conn:
        user = conn.execute(
            "SELECT id, full_name, phone, email, balance FROM app_user WHERE id = %s",
            (user_id,),
        ).fetchone()
    if not user:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    user["balance"] = str(user["balance"])
    return user


@app.post(
    "/internal/accounts/{user_id}/reserve",
    dependencies=[Depends(require_service_token)],
)
def reserve_balance(user_id: int, body: Reservation):
    with database("auth_database") as conn:
        # Serialize retries for one transaction before checking or changing the balance.
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (body.transaction_code,),
        )
        existing = conn.execute(
            "SELECT user_id, amount, status FROM account_reservation WHERE transaction_code = %s FOR UPDATE",
            (body.transaction_code,),
        ).fetchone()
        if existing:
            if existing["user_id"] != user_id or existing["amount"] != body.amount:
                raise HTTPException(409, "Mã giao dịch đã được dùng cho thông tin khác")
            if existing["status"] in ("reserved", "committed"):
                return {"status": existing["status"]}
            raise HTTPException(409, "Khoản giữ tiền đã được hủy")

        user = conn.execute(
            "SELECT balance FROM app_user WHERE id = %s FOR UPDATE", (user_id,)
        ).fetchone()
        if not user:
            raise HTTPException(404, "Không tìm thấy tài khoản")
        if user["balance"] < body.amount:
            raise HTTPException(409, "Số dư khả dụng không đủ")
        conn.execute(
            "UPDATE app_user SET balance = balance - %s, version = version + 1 WHERE id = %s",
            (body.amount, user_id),
        )
        conn.execute(
            "INSERT INTO account_reservation (transaction_code, user_id, amount, status) VALUES (%s, %s, %s, 'reserved')",
            (body.transaction_code, user_id, body.amount),
        )
    return {"status": "reserved"}


@app.post(
    "/internal/accounts/reservations/{transaction_code}/commit",
    dependencies=[Depends(require_service_token)],
)
def commit_reservation(transaction_code: str):
    with database("auth_database") as conn:
        row = conn.execute(
            "SELECT status FROM account_reservation WHERE transaction_code = %s FOR UPDATE",
            (transaction_code,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Không tìm thấy khoản giữ tiền")
        if row["status"] == "released":
            raise HTTPException(409, "Khoản giữ tiền đã được hoàn lại")
        if row["status"] == "reserved":
            conn.execute(
                "UPDATE account_reservation SET status = 'committed', updated_at = CURRENT_TIMESTAMP WHERE transaction_code = %s",
                (transaction_code,),
            )
    return {"status": "committed"}


@app.post(
    "/internal/accounts/reservations/{transaction_code}/release",
    dependencies=[Depends(require_service_token)],
)
def release_reservation(transaction_code: str):
    with database("auth_database") as conn:
        row = conn.execute(
            "SELECT user_id, amount, status FROM account_reservation WHERE transaction_code = %s FOR UPDATE",
            (transaction_code,),
        ).fetchone()
        if not row:
            return {"status": "not_reserved"}
        if row["status"] == "committed":
            raise HTTPException(
                409, "Giao dịch đã hoàn tất, không thể tự động hoàn lại"
            )
        if row["status"] == "reserved":
            conn.execute(
                "UPDATE app_user SET balance = balance + %s, version = version + 1 WHERE id = %s",
                (row["amount"], row["user_id"]),
            )
            conn.execute(
                "UPDATE account_reservation SET status = 'released', updated_at = CURRENT_TIMESTAMP WHERE transaction_code = %s",
                (transaction_code,),
            )
    return {"status": "released"}

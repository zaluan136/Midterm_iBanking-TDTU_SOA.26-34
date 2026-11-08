from fastapi import Depends, HTTPException, Path
from pydantic import BaseModel, Field
from services.common import make_app, database, current_user, require_service_token

app = make_app("iBanking Tuition")
from services.demo_admin import attach_tuition

attach_tuition(app)


class PaymentMark(BaseModel):
    transaction_code: str = Field(min_length=1, max_length=64)


@app.get("/api/tuition/{mssv}")
def lookup(
    mssv: str = Path(min_length=1, max_length=20), user_id: int = Depends(current_user)
):
    with database("tuition_database") as conn:
        rows = conn.execute(
            "SELECT id, mssv, student_name, amount, semester, status FROM tuition_fee WHERE mssv = %s ORDER BY id",
            (mssv.strip(),),
        ).fetchall()
    if not rows:
        raise HTTPException(404, "Không tìm thấy học phí cho MSSV này")
    for row in rows:
        row["amount"] = str(row["amount"])
    return rows


@app.get("/internal/tuition/{fee_id}", dependencies=[Depends(require_service_token)])
def get_fee(fee_id: int):
    with database("tuition_database") as conn:
        row = conn.execute(
            "SELECT id, mssv, student_name, amount, semester, status FROM tuition_fee WHERE id = %s",
            (fee_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Không tìm thấy khoản học phí")
    row["amount"] = str(row["amount"])
    return row


@app.post(
    "/internal/tuition/{fee_id}/pay", dependencies=[Depends(require_service_token)]
)
def mark_paid(fee_id: int, body: PaymentMark):
    transaction_code = body.transaction_code
    with database("tuition_database") as conn:
        row = conn.execute(
            "UPDATE tuition_fee SET status = 'paid', payment_transaction_code = %s, version = version + 1 "
            "WHERE id = %s AND status = 'unpaid' RETURNING id, status, payment_transaction_code",
            (transaction_code, fee_id),
        ).fetchone()
        if not row:
            current = conn.execute(
                "SELECT id, status, payment_transaction_code FROM tuition_fee WHERE id = %s FOR UPDATE",
                (fee_id,),
            ).fetchone()
            if not current:
                raise HTTPException(404, "Không tìm thấy khoản học phí")
            if (
                current["status"] == "paid"
                and current["payment_transaction_code"] == transaction_code
            ):
                row = current  # Retry of the same saga step.
            else:
                raise HTTPException(409, "Khoản học phí đã được thanh toán")
    return row

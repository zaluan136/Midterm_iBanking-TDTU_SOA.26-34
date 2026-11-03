from fastapi import Depends, HTTPException, Path
from services.common import make_app, database, current_user

app = make_app('iBanking Tuition')


@app.get('/api/tuition/{mssv}')
def lookup(mssv: str = Path(min_length=1, max_length=20), user_id: int = Depends(current_user)):
    with database('tuition_database') as conn:
        rows = conn.execute('SELECT id, mssv, student_name, amount, semester, status FROM tuition_fee WHERE mssv = %s ORDER BY id', (mssv.strip(),)).fetchall()
    if not rows:
        raise HTTPException(404, 'Không tìm thấy học phí cho MSSV này')
    for row in rows:
        row['amount'] = str(row['amount'])
    return rows


from services.internal_payment import MarkPaid, internal_auth


@app.get('/internal/tuition/{fee_id}', dependencies=[Depends(internal_auth)])
def fee_info(fee_id: int):
    with database('tuition_database') as conn:
        row = conn.execute('SELECT * FROM tuition_fee WHERE id=%s', (fee_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Không tìm thấy khoản học phí')
    row['amount'] = str(row['amount'])
    return row


@app.post('/internal/tuition/mark-paid', dependencies=[Depends(internal_auth)])
def mark_paid(body: MarkPaid):
    with database('tuition_database') as conn:
        row = conn.execute('SELECT * FROM tuition_fee WHERE id=%s FOR UPDATE', (body.tuition_fee_id,)).fetchone()
        if row and row['paid_by_transaction'] == body.transaction_code:
            return {'ok': True}
        if not row or row['status'] != 'unpaid' or row['amount'] != body.amount:
            raise HTTPException(409, 'Học phí đã thanh toán hoặc đã thay đổi')
        conn.execute("UPDATE tuition_fee SET status='paid',version=version+1,paid_by_transaction=%s WHERE id=%s", (body.transaction_code,body.tuition_fee_id))
    return {'ok': True}

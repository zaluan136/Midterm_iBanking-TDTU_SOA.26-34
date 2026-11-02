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

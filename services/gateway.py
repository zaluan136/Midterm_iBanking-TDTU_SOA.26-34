from pathlib import Path
import httpx
from fastapi import Request, Depends
from fastapi.responses import FileResponse, Response, JSONResponse
from services.common import make_app, current_user

app = make_app('iBanking Gateway')


async def forward(request, port):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            result = await client.request(request.method, f'http://127.0.0.1:{port}{request.url.path}', content=await request.body(), headers={'Content-Type': 'application/json', 'Authorization': request.headers.get('Authorization', '')})
        return Response(result.content, status_code=result.status_code, media_type='application/json')
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={'detail': 'Service chưa sẵn sàng, vui lòng thử lại.'})


@app.get('/')
def home():
    return FileResponse(Path(__file__).resolve().parents[1] / 'web' / 'index.html')


@app.post('/api/auth/login')
async def login(request: Request):
    return await forward(request, 8001)


@app.get('/api/account/info', dependencies=[Depends(current_user)])
async def account(request: Request):
    return await forward(request, 8001)


@app.get('/api/tuition/{mssv}', dependencies=[Depends(current_user)])
async def tuition(mssv: str, request: Request):
    return await forward(request, 8003)

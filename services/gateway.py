from pathlib import Path
import httpx
import os
from fastapi import Request, Depends, HTTPException
from fastapi.responses import FileResponse, Response, JSONResponse
from services.common import make_app, current_user

app = make_app("iBanking Gateway")


@app.api_route(
    "/api/demo/{resource}",
    methods=["GET", "POST"],
    dependencies=[Depends(current_user)],
)
async def demo(resource: str, request: Request):
    if os.getenv("DEMO_ADMIN") != "1" or resource not in ("accounts", "tuition"):
        raise HTTPException(404)
    return await forward(request, 8001 if resource == "accounts" else 8003)


@app.get("/app.js")
def script():
    return FileResponse(
        Path(__file__).resolve().parents[1] / "web" / "app.js",
        media_type="application/javascript",
    )


@app.get("/app.css")
def stylesheet():
    return FileResponse(
        Path(__file__).resolve().parents[1] / "web" / "app.css", media_type="text/css"
    )


async def forward(request, port):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            service = {8001: "AUTH_ACCOUNT", 8002: "PAYMENT", 8003: "TUITION"}[port]
            base_url = os.getenv(f"{service}_SERVICE_URL", f"http://127.0.0.1:{port}")
            target = base_url.rstrip("/") + request.url.path
            if request.url.query:
                target += "?" + request.url.query
            result = await client.request(
                request.method,
                target,
                content=await request.body(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": request.headers.get("Authorization", ""),
                },
            )
        return Response(
            result.content,
            status_code=result.status_code,
            media_type="application/json",
        )
    except httpx.RequestError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Service chưa sẵn sàng, vui lòng thử lại."},
        )


@app.get("/")
def home():
    return FileResponse(Path(__file__).resolve().parents[1] / "web" / "index.html")


@app.post("/api/auth/login")
async def login(request: Request):
    return await forward(request, 8001)


@app.get("/api/account/info", dependencies=[Depends(current_user)])
async def account(request: Request):
    return await forward(request, 8001)


@app.get("/api/tuition/{mssv}", dependencies=[Depends(current_user)])
async def tuition(mssv: str, request: Request):
    return await forward(request, 8003)


@app.post("/api/payments")
async def start_payment(request: Request, user_id: int = Depends(current_user)):
    return await forward(request, 8002)


@app.post("/api/payments/{transaction_code}/otp/resend")
async def resend_otp(
    transaction_code: str, request: Request, user_id: int = Depends(current_user)
):
    return await forward(request, 8002)


@app.post("/api/payments/{transaction_code}/confirm")
async def confirm_payment(
    transaction_code: str, request: Request, user_id: int = Depends(current_user)
):
    return await forward(request, 8002)


@app.post("/api/payments/{transaction_code}/receipt/resend")
async def resend_receipt(
    transaction_code: str, request: Request, user_id: int = Depends(current_user)
):
    return await forward(request, 8002)


@app.get("/api/payments/{transaction_code}")
async def payment_status(
    transaction_code: str, request: Request, user_id: int = Depends(current_user)
):
    return await forward(request, 8002)


@app.get("/api/account/transactions")
async def payment_history(request: Request, user_id: int = Depends(current_user)):
    return await forward(request, 8002)

from fastapi import FastAPI, Depends, HTTPException, Request, Response, Cookie
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import os
from typing import Optional, Dict, Any
import uuid
from pydantic import BaseModel
from starlette.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import aiohttp
import urllib3
from urllib3.exceptions import MaxRetryError, TimeoutError
import asyncio
from concurrent.futures import ThreadPoolExecutor
import httpcore
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="BFF API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for session data (Redis substitute for demo)
session_store: Dict[str, Dict[str, Any]] = {}

# Backend API URL
BACKEND_API_URL = "http://localhost:8000"

# Auth header handling
API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)

# カスタムエラーレスポンスの形式
class ErrorResponse(BaseModel):
    status_code: int
    message: str
    details: Optional[Any] = None
    error_code: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthData(BaseModel):
    user_id: str
    username: str
    roles: list[str]

# カスタムエラーハンドラー
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTPエラーのハンドラー"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status_code=exc.status_code,
            message=str(exc.detail),
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """バリデーションエラーのハンドラー"""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            status_code=422,
            message="入力データのバリデーションエラー",
            details=exc.errors(),
            error_code="VALIDATION_ERROR"
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般的な例外のハンドラー"""
    # 本番環境ではログに詳細を記録する
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            status_code=500,
            message="サーバー内部エラー",
            error_code="INTERNAL_SERVER_ERROR"
        ).dict()
    )

def get_auth_data(request: Request) -> Optional[AuthData]:
    """Get authentication data from the session store based on cookie"""
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in session_store:
        return None
    
    auth_data = session_store.get(session_id)
    if not auth_data:
        return None
    
    return AuthData(**auth_data)

async def auth_required(auth_data: Optional[AuthData] = Depends(get_auth_data)):
    """Dependency to enforce authentication"""
    if auth_data is None:
        raise HTTPException(
            status_code=401, 
            detail="認証されていません。ログインしてください。",
        )
    return auth_data

@app.get("/")
def read_root():
    return {"message": "BFF API is running"}

@app.post("/auth/login")
async def login(login_data: LoginRequest, response: Response):
    """Login endpoint that creates a session"""
    # In a real app, verify credentials against a database
    # This is a mock that accepts any username/password
    
    # Mock user data - in a real app this would come from a database
    if login_data.username and login_data.password:
        # Create session
        session_id = str(uuid.uuid4())
        user_data = {
            "user_id": str(uuid.uuid4()),
            "username": login_data.username,
            "roles": ["user"]
        }
        
        # Store in our "Redis" (in-memory dict)
        session_store[session_id] = user_data
        
        # Set cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=1800,  # 30 minutes
            samesite="lax",
            secure=False,  # Set to True in production with HTTPS
        )
        
        return {"message": "Login successful", "user": user_data}
    
    raise HTTPException(
        status_code=401, 
        detail="ユーザー名またはパスワードが無効です",
    )

@app.get("/auth/logout")
def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    """Logout endpoint that clears the session"""
    if session_id and session_id in session_store:
        # Remove from our "Redis"
        del session_store[session_id]
    
    # Clear cookie
    response.delete_cookie(key="session_id")
    return {"message": "Logged out successfully"}

@app.get("/auth/me")
async def get_current_user(auth_data: AuthData = Depends(auth_required)):
    """Return current authenticated user data"""
    return auth_data

# 以下の個別のAPI エンドポイントを削除
# @app.get("/api/items")
# @app.get("/api/items/{item_id}")
# @app.post("/api/items")

# 代わりに全てのエンドポイントを受け入れて転送するキャッチオールルートを追加

# HTTPプールの作成
http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5.0, read=10.0))

# 同期処理を非同期に変換するためのエグゼキューター
executor = ThreadPoolExecutor(max_workers=10)

async def send_request(method, url, fields=None, headers=None, body=None):
    """urllib3のリクエストを非同期に実行するためのヘルパー関数"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        lambda: http.request(
            method=method,
            url=url,
            fields=fields,
            headers=headers,
            body=body,
            redirect=False,
            retries=3
        )
    )

async def proxy_stream(request, target_url, headers):
    """リクエストボディとレスポンスを非同期にストリーミングするヘルパー関数"""
    # リクエストボディの読み取り
    body = await request.body()
    
    # シンプルなHTTP接続
    async with httpcore.AsyncConnectionPool() as http:
        response = await http.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body
        )
        
        # レスポンスヘッダーの処理
        resp_headers = {}
        for key, value in response.headers:
            if key.lower() not in ("transfer-encoding", "content-encoding", "content-length"):
                resp_headers[key.decode('latin1')] = value.decode('latin1')
        
        # ストリーミングレスポンスの返却
        return StreamingResponse(
            content=response.stream(),
            status_code=response.status,
            headers=resp_headers
        )

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_all_routes(request: Request, path: str, auth_data: AuthData = Depends(auth_required)):
    """あらゆるAPIリクエストをバックエンドに転送する"""
    # サーキットブレーカーチェック...
    
    # リクエスト情報の収集
    method = request.method
    url = f"{BACKEND_API_URL}/{path}"
    
    # クエリパラメータの処理
    if request.query_params:
        query_string = str(request.query_params)
        url = f"{url}?{query_string}"
    
    # ヘッダーの準備
    headers = {}
    for name, value in request.headers.items():
        if name.lower() not in ("host", "cookie", "authorization"):
            headers[name] = value
    
    # ボディの取得
    body = await request.body() if method in ["POST", "PUT", "PATCH"] else None
    
    try:
        # バックエンドへのリクエスト送信
        logger.info(f"Proxying request to backend: {method} {url}")
        response = await send_request(
            method=method,
            url=url,
            headers=headers,
            body=body
        )
        
        # レスポンスヘッダーの処理
        resp_headers = {}
        for name, value in response.headers.items():
            if name.lower() not in ("transfer-encoding", "content-encoding", "content-length"):
                resp_headers[name] = value
        
        # # 成功したらサーキットブレーカーをリセット
        # backend_circuit.record_success()
        
        # レスポンスの返却
        return Response(
            content=response.data,
            status_code=response.status,
            headers=resp_headers,
            media_type=response.headers.get("content-type")
        )
        
    except (MaxRetryError, TimeoutError) as e:
        # 接続/タイムアウトエラーの処理...
        pass
        
    except Exception as e:
        # その他のエラー処理...
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 
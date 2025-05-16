from fastapi import FastAPI, Depends, HTTPException, Request, Response, Cookie
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import os
import time
import asyncio
import logging
import traceback
from typing import Optional, Dict, Any
import uuid
from pydantic import BaseModel
from starlette.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# ロガーの設定
logger = logging.getLogger("bff")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

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

# サーキットブレーカークラス
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_time=30):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = None
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def record_success(self):
        if self.state == "HALF_OPEN":
            logger.info("Circuit breaker recovered and closed")
        self.failure_count = 0
        self.state = "CLOSED"
    
    def allow_request(self):
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            # 回復時間が経過したら半開状態に
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker state changed to HALF_OPEN")
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False

# グローバルなサーキットブレーカーインスタンス
backend_circuit = CircuitBreaker()

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
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
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
    logger.error(f"Validation Error: {exc.errors()}")
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
    # 詳細なエラーログを記録
    error_traceback = traceback.format_exc()
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client": request.client.host if request.client else None
    }
    
    logger.error(
        f"Unhandled exception: {str(exc)}\n"
        f"Request: {request_info}\n"
        f"Traceback: {error_traceback}"
    )
    
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
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"], status_code=200)
async def proxy_all_routes(request: Request, path: str, auth_data: AuthData = Depends(auth_required)):
    """あらゆるAPIリクエストをバックエンドに転送する"""
    # サーキットブレーカーチェック
    if not backend_circuit.allow_request():
        logger.warning(f"Circuit breaker is open - rejecting request to {path}")
        raise HTTPException(
            status_code=503,
            detail={
                "message": "バックエンドサービスは現在利用できません",
                "error_code": "CIRCUIT_OPEN"
            }
        )
    
    # 改善されたHTTPXクライアントの設定
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0)  # 接続タイムアウトを個別に設定
    )
    
    # リクエストのメソッドを取得
    method = request.method
    
    # クエリパラメータを取得
    url = f"{BACKEND_API_URL}/{path}"
    params = dict(request.query_params)
    
    # リクエストヘッダーを取得 (認証情報やCookieは除く)
    headers = {}
    for name, value in request.headers.items():
        if name.lower() not in ("host", "cookie", "authorization"):
            headers[name] = value
    
    # リクエストボディを取得
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
        if not body:
            body = None
    
    # リトライロジックの追加
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # バックエンドにリクエストを転送
            logger.info(f"Proxying request to backend: {method} {url}")
            response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                content=body,
            )
            
            # レスポンスヘッダーを作成
            resp_headers = {}
            for name, value in response.headers.items():
                if name.lower() not in ("transfer-encoding", "content-encoding", "content-length"):
                    resp_headers[name] = value
            
            # 成功したらサーキットブレーカーをリセット
            backend_circuit.record_success()
            
            # バックエンドからのレスポンスをそのまま返す
            logger.info(f"Backend responded with status: {response.status_code}")
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=resp_headers,
                media_type=response.headers.get("content-type")
            )
            
        except httpx.ConnectError as e:
            # 接続エラーはリトライ
            retry_count += 1
            logger.warning(f"Connection error to backend (attempt {retry_count}/{max_retries}): {str(e)}")
            
            if retry_count >= max_retries:
                backend_circuit.record_failure()
                raise HTTPException(
                    status_code=503,
                    detail={
                        "message": "バックエンドサービスに接続できません",
                        "details": str(e),
                        "error_code": "BACKEND_CONNECTION_ERROR"
                    }
                )
            # リトライ前に少し待機
            await asyncio.sleep(0.5 * retry_count)  # 徐々に待機時間を増やす
            
        except httpx.TimeoutException as e:
            # タイムアウトエラーの処理を分離
            logger.error(f"Timeout error to backend: {str(e)}")
            backend_circuit.record_failure()
            raise HTTPException(
                status_code=504,
                detail={
                    "message": "バックエンドサービスの応答がタイムアウトしました",
                    "details": str(e),
                    "error_code": "BACKEND_TIMEOUT"
                }
            )
            
        except httpx.HTTPStatusError as e:
            # HTTP エラー（404, 500など）を整形して返す
            logger.error(f"HTTP status error from backend: {e.response.status_code}")
            error_message = "バックエンドAPIエラー"
            error_details = None
            
            try:
                # JSONレスポンスの場合、詳細情報を抽出
                error_content = e.response.json()
                if isinstance(error_content, dict) and "detail" in error_content:
                    error_message = error_content["detail"]
                error_details = error_content
            except:
                # JSONでない場合はテキストを使用
                error_message = e.response.text or error_message
            
            # 重大なエラーの場合はサーキットブレーカーに記録
            if e.response.status_code >= 500:
                backend_circuit.record_failure()
            
            # カスタムエラーレスポンスを生成
            raise HTTPException(
                status_code=e.response.status_code,
                detail={
                    "message": error_message,
                    "details": error_details,
                    "error_code": f"BACKEND_{e.response.status_code}"
                }
            )
            
        except httpx.RequestError as e:
            # その他のリクエストエラー
            logger.error(f"Request error to backend: {str(e)}")
            backend_circuit.record_failure()
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "バックエンドサービスに接続できません",
                    "details": str(e),
                    "error_code": "BACKEND_CONNECTION_ERROR"
                }
            )
        finally:
            await client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 
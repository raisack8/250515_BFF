from fastapi import FastAPI, Depends, HTTPException, Request, Response, Cookie
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import os
from typing import Optional, Dict, Any
import uuid
from pydantic import BaseModel

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

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthData(BaseModel):
    user_id: str
    username: str
    roles: list[str]

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
        raise HTTPException(status_code=401, detail="Not authenticated")
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
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

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

@app.get("/api/items")
async def proxy_items(auth_data: AuthData = Depends(auth_required)):
    """Proxy the /items endpoint from the backend API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_API_URL}/items")
        return response.json()

@app.get("/api/items/{item_id}")
async def proxy_item(item_id: int, auth_data: AuthData = Depends(auth_required)):
    """Proxy the /items/{item_id} endpoint from the backend API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_API_URL}/items/{item_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Item not found")
        return response.json()

@app.post("/api/items")
async def proxy_create_item(item: Dict[str, Any], auth_data: AuthData = Depends(auth_required)):
    """Proxy the POST /items endpoint from the backend API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BACKEND_API_URL}/items", json=item)
        return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 
import os
import hmac
import hashlib
import base64
import json
import time
import requests
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header, Depends, status
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from backend.agent import CodeGeneratorAgent
from backend.code_executor import execute_python_code
from backend.code_validator import validate_python_code

load_dotenv()

APP_ACCESS_API_KEY = os.getenv("APP_ACCESS_API_KEY", "ist-cia-secret-key-2026")
AUTH_SECRET = os.getenv("AUTH_SECRET", "svyasa-genai-jwt-secret-2026")

# Demo Users Store (Can also be configured via env)
DEMO_USERS = {
    "biswajit": "ist2026",
    "faculty": "admin123",
    "student": "genai2026"
}

app = FastAPI(
    title="AI Code Generator Agent API (CIA-P)",
    description="User Authenticated REST API with Self-Healing Python Sandbox and Webhooks.",
    version="3.0.0"
)

# --- 1. STATELESS TOKEN & API KEY AUTH ---
def create_auth_token(username: str) -> str:
    payload = json.dumps({"sub": username, "exp": int(time.time()) + 86400}).encode()
    b64_payload = base64.urlsafe_b64encode(payload).decode()
    sig = hmac.new(AUTH_SECRET.encode(), b64_payload.encode(), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{sig}"

def verify_auth_token(token: str) -> Optional[str]:
    try:
        b64_payload, sig = token.split(".")
        expected_sig = hmac.new(AUTH_SECRET.encode(), b64_payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        data = json.loads(base64.urlsafe_b64decode(b64_payload).decode())
        if data.get("exp", 0) < time.time():
            return None
        return data.get("sub")
    except Exception:
        return None

def authenticate_request(
    x_api_key: Optional[str] = Header(default=None, description="API Key for external apps"),
    authorization: Optional[str] = Header(default=None, description="Bearer token from /api/login")
):
    # Check 1: Valid X-API-Key
    if x_api_key and x_api_key == APP_ACCESS_API_KEY:
        return "api_key_user"
    # Check 2: Valid User Login Bearer Token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        user = verify_auth_token(token)
        if user:
            return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Please login first or provide a valid X-API-Key."
    )

# --- 2. SCHEMAS ---
class LoginRequest(BaseModel):
    username: str = Field(..., example="biswajit")
    password: str = Field(..., example="ist2026")

class GenerateCodeRequest(BaseModel):
    prompt: str = Field(..., example="Write a Python function for binary search with test cases")
    auto_execute: bool = Field(default=True)
    webhook_url: Optional[HttpUrl] = Field(default=None, example="https://webhook.site/your-id")

class ExecuteCodeRequest(BaseModel):
    code: str = Field(..., example="print('Hello World')")
    timeout_seconds: Optional[int] = 5

class AgentResponse(BaseModel):
    success: bool
    plan: Optional[str] = ""
    code: Optional[str] = ""
    explanation: Optional[str] = ""
    stdout: Optional[str] = ""
    error: Optional[str] = None
    retries_taken: int = 0
    webhook_status: Optional[str] = "Not configured"
    history: List[Dict[str, Any]] = []

# --- 3. WEBHOOK DISPATCHER ---
def trigger_webhook(webhook_url: str, event_type: str, payload_data: Dict[str, Any]) -> str:
    webhook_body = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_code": 200 if payload_data.get("success") else 422,
        "data": {
            "success": payload_data.get("success"),
            "code": payload_data.get("code"),
            "stdout": payload_data.get("stdout"),
            "retries_taken": payload_data.get("retries_taken"),
            "error": payload_data.get("error")
        }
    }
    try:
        resp = requests.post(
            str(webhook_url),
            json=webhook_body,
            headers={"Content-Type": "application/json", "X-Agent-Event": event_type},
            timeout=5
        )
        return f"Delivered (HTTP {resp.status_code})"
    except Exception as e:
        return f"Delivery Failed ({str(e)})"

# --- 4. ENDPOINTS ---
@app.get("/", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "online", "service": "AI Code Generator Agent", "auth": "User Login + X-API-Key"}

@app.post("/api/login", status_code=status.HTTP_200_OK)
def login_endpoint(creds: LoginRequest):
    username = creds.username.strip().lower()
    if username in DEMO_USERS and DEMO_USERS[username] == creds.password:
        token = create_auth_token(username)
        return {
            "success": True,
            "username": username,
            "access_token": token,
            "token_type": "bearer"
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password."
    )

@app.post("/api/generate", response_model=AgentResponse, status_code=status.HTTP_200_OK)
def generate_code_endpoint(payload: GenerateCodeRequest, current_user: str = Depends(authenticate_request)):
    if not payload.prompt.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt cannot be empty.")

    agent = CodeGeneratorAgent()
    result = agent.run(user_prompt=payload.prompt, auto_execute=payload.auto_execute)

    if payload.webhook_url:
        event_name = "code.generation.completed" if result.get("success") else "code.generation.failed"
        result["webhook_status"] = trigger_webhook(str(payload.webhook_url), event_name, result)
    else:
        result["webhook_status"] = "Not provided"

    return result

@app.post("/api/execute", status_code=status.HTTP_200_OK)
def execute_code_endpoint(payload: ExecuteCodeRequest, current_user: str = Depends(authenticate_request)):
    is_valid, error_msg = validate_python_code(payload.code)
    if not is_valid:
        return {"success": False, "stdout": "", "stderr": error_msg, "exit_code": -1, "timed_out": False}
    return execute_python_code(payload.code, timeout_seconds=payload.timeout_seconds)

import os
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

app = FastAPI(
    title="AI Code Generator Agent API (CIA-P)",
    description="Authenticated REST API with Self-Healing Python Sandbox and Webhook Notifications.",
    version="2.0.0"
)

# --- 1. API KEY AUTHENTICATION MECHANISM ---
def verify_api_key(x_api_key: str = Header(..., description="API Key required to access endpoints")):
    if x_api_key != APP_ACCESS_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header."
        )
    return x_api_key

# --- 2. REQUEST & RESPONSE SCHEMAS ---
class GenerateCodeRequest(BaseModel):
    prompt: str = Field(..., example="Write a Python function for binary search with test cases")
    auto_execute: bool = Field(default=True)
    webhook_url: Optional[HttpUrl] = Field(
        default=None, 
        example="https://webhook.site/your-unique-id",
        description="Optional external URL to receive JSON event updates via HTTP POST"
    )

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
    """Sends structured JSON payload to the registered webhook URL."""
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

# --- 4. API ENDPOINTS ---
@app.get("/", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "online",
        "service": "AI Code Generator Agent",
        "auth_required": "X-API-Key header on /api/* routes"
    }

@app.post("/api/generate", response_model=AgentResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(verify_api_key)])
def generate_code_endpoint(payload: GenerateCodeRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt cannot be empty.")
    
    agent = CodeGeneratorAgent()
    result = agent.run(user_prompt=payload.prompt, auto_execute=payload.auto_execute)

    # Trigger Webhook if URL provided
    if payload.webhook_url:
        event_name = "code.generation.completed" if result.get("success") else "code.generation.failed"
        result["webhook_status"] = trigger_webhook(str(payload.webhook_url), event_name, result)
    else:
        result["webhook_status"] = "Not provided"

    return result

@app.post("/api/execute", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_api_key)])
def execute_code_endpoint(payload: ExecuteCodeRequest):
    is_valid, error_msg = validate_python_code(payload.code)
    if not is_valid:
        return {
            "success": False,
            "stdout": "",
            "stderr": error_msg,
            "exit_code": -1,
            "timed_out": False
        }
    return execute_python_code(payload.code, timeout_seconds=payload.timeout_seconds)
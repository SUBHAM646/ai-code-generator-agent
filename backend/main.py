from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from backend.agent import CodeGeneratorAgent
from backend.code_executor import execute_python_code
from backend.code_validator import validate_python_code

app = FastAPI(
    title="AI Code Generator Agent API",
    description="Backend API powered by LLM agent with self-healing code execution and validation.",
    version="1.0.0"
)

# Request & Response Schemas
class GenerateCodeRequest(BaseModel):
    prompt: str = Field(..., example="Write a binary search algorithm in Python with tests")
    auto_execute: bool = Field(default=True, description="Whether to execute code in sandbox")

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
    history: List[Dict[str, Any]] = []

@app.get("/")
def health_check():
    return {"status": "online", "service": "AI Code Generator Agent"}

@app.post("/api/generate", response_model=AgentResponse)
def generate_code_endpoint(payload: GenerateCodeRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    agent = CodeGeneratorAgent()
    result = agent.run(user_prompt=payload.prompt, auto_execute=payload.auto_execute)
    return result

@app.post("/api/execute")
def execute_code_endpoint(payload: ExecuteCodeRequest):
    # Static AST check before running
    is_valid, error_msg = validate_python_code(payload.code)
    if not is_valid:
        return {
            "success": False,
            "stdout": "",
            "stderr": error_msg,
            "exit_code": -1,
            "timed_out": False
        }
    
    # Run sandbox
    return execute_python_code(payload.code, timeout_seconds=payload.timeout_seconds)
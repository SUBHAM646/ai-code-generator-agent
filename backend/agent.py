import os
from typing import Dict, Any, List
from backend.prompts import SYSTEM_CODE_GENERATOR_PROMPT, ERROR_CORRECTION_PROMPT_TEMPLATE
from backend.code_generator import generate_code_response
from backend.code_validator import validate_python_code
from backend.code_executor import execute_python_code

MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
EXEC_TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", 5))

class CodeGeneratorAgent:
    def __init__(self, max_retries: int = MAX_RETRIES):
        self.max_retries = max_retries

    def run(self, user_prompt: str, auto_execute: bool = True) -> Dict[str, Any]:
        """
        Agentic Workflow:
        1. Generate Initial Code & Plan
        2. Validate AST & Security
        3. Execute in Sandbox
        4. Loop: If error found -> Self-Correct via LLM Reflection
        """
        history_logs: List[Dict[str, Any]] = []
        current_prompt = user_prompt
        attempt = 0

        # Initial Generation
        generation = generate_code_response(SYSTEM_CODE_GENERATOR_PROMPT, current_prompt)
        code = generation["code"]
        plan = generation["plan"]
        explanation = generation["explanation"]

        while attempt <= self.max_retries:
            attempt += 1
            log_entry = {
                "attempt": attempt,
                "code": code,
                "status": "in_progress",
                "error": None
            }

            # 1. AST Validation Check
            is_valid, val_error = validate_python_code(code)
            if not is_valid:
                log_entry["status"] = "ast_validation_failed"
                log_entry["error"] = val_error
                history_logs.append(log_entry)

                if attempt > self.max_retries:
                    break

                # Self-healing prompt
                correction_prompt = ERROR_CORRECTION_PROMPT_TEMPLATE.format(
                    user_prompt=user_prompt,
                    previous_code=code,
                    error_message=val_error
                )
                generation = generate_code_response(SYSTEM_CODE_GENERATOR_PROMPT, correction_prompt)
                code = generation["code"]
                continue

            # 2. Sandbox Execution (if requested)
            if auto_execute:
                exec_result = execute_python_code(code, timeout_seconds=EXEC_TIMEOUT)
                if not exec_result["success"]:
                    error_msg = exec_result["stderr"]
                    log_entry["status"] = "execution_failed"
                    log_entry["error"] = error_msg
                    history_logs.append(log_entry)

                    if attempt > self.max_retries:
                        break

                    correction_prompt = ERROR_CORRECTION_PROMPT_TEMPLATE.format(
                        user_prompt=user_prompt,
                        previous_code=code,
                        error_message=error_msg
                    )
                    generation = generate_code_response(SYSTEM_CODE_GENERATOR_PROMPT, correction_prompt)
                    code = generation["code"]
                    continue
                else:
                    log_entry["status"] = "success"
                    log_entry["stdout"] = exec_result["stdout"]
                    history_logs.append(log_entry)
                    return {
                        "success": True,
                        "plan": plan,
                        "code": code,
                        "explanation": explanation,
                        "stdout": exec_result["stdout"],
                        "retries_taken": attempt - 1,
                        "history": history_logs
                    }
            else:
                log_entry["status"] = "validated_without_execution"
                history_logs.append(log_entry)
                return {
                    "success": True,
                    "plan": plan,
                    "code": code,
                    "explanation": explanation,
                    "stdout": "Code validated successfully (execution skipped).",
                    "retries_taken": attempt - 1,
                    "history": history_logs
                }

        return {
            "success": False,
            "plan": plan,
            "code": code,
            "explanation": explanation,
            "error": history_logs[-1]["error"] if history_logs else "Unknown execution failure.",
            "retries_taken": attempt - 1,
            "history": history_logs
        }
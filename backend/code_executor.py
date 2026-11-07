import subprocess
import tempfile
import os
from typing import Dict, Any

def execute_python_code(code: str, timeout_seconds: int = 5) -> Dict[str, Any]:
    """
    Executes Python code in an isolated subprocess with a strict timeout.
    Returns:
    {
        "success": bool,
        "stdout": str,
        "stderr": str,
        "exit_code": int,
        "timed_out": bool
    }
    """
    # Temporary file create karo execution ke liye
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        # Isolated process trigger karo
        process = subprocess.run(
            ["python", temp_file_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding="utf-8",
            errors="replace"
        )
        
        return {
            "success": process.returncode == 0,
            "stdout": process.stdout.strip(),
            "stderr": process.stderr.strip(),
            "exit_code": process.returncode,
            "timed_out": False
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution Timed Out: Code exceeded the limit of {timeout_seconds} seconds (possible infinite loop).",
            "exit_code": -1,
            "timed_out": True
        }

    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"System Execution Error: {str(e)}",
            "exit_code": -1,
            "timed_out": False
        }

    finally:
        # Har halaat mein temp file cleanup karo
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
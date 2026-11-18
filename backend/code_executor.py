import subprocess
import tempfile
import os
import sys
from typing import Dict, Any

def execute_python_code(code: str, timeout_seconds: int = 5) -> Dict[str, Any]:
    """Executes Python code in an isolated subprocess using /tmp directory."""
    temp_dir = "/tmp" if os.path.exists("/tmp") else None
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8", dir=temp_dir
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        result = subprocess.run(
            [sys.executable, temp_file_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode,
            "timed_out": False
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution Timed Out: Exceeded {timeout_seconds} seconds limit.",
            "exit_code": -1,
            "timed_out": True
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Sandbox System Error: {str(e)}",
            "exit_code": -1,
            "timed_out": False
        }
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass

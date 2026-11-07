import ast
from typing import Tuple, List

# Security: In modules aur functions ko execution se pehle hi block karenge
BLOCKED_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", 
    "requests", "urllib", "pty", "commands"
}

BLOCKED_BUILTINS = {
    "eval", "exec", "compile", "__import__"
}

def validate_python_code(code: str) -> Tuple[bool, str]:
    """
    Validates Python code using Abstract Syntax Tree (AST).
    Checks for:
    1. Syntax validity
    2. Interactive input() calls (which freeze automated backends)
    3. Blocked malicious imports/calls
    Returns (is_valid: bool, error_message: str)
    """
    if not code or not code.strip():
        return False, "Validation Error: Code is empty."

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error at line {e.lineno}, offset {e.offset}: {e.msg}"

    # AST Nodes traverse karke dangerous patterns dhundte hain
    for node in ast.walk(tree):
        # 1. Block imports like: import os, sys
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split('.')[0]
                if root_module in BLOCKED_MODULES:
                    return False, f"Security Violation: Import of module '{root_module}' is restricted."

        # 2. Block imports like: from os import system
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split('.')[0]
                if root_module in BLOCKED_MODULES:
                    return False, f"Security Violation: Import from module '{root_module}' is restricted."

        # 3. Detect and block input(), eval(), exec()
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name == "input":
                    return False, "Runtime Constraint: Interactive 'input()' is not supported. Use static test driver arguments instead."
                if func_name in BLOCKED_BUILTINS:
                    return False, f"Security Violation: Function '{func_name}()' is blocked."

    return True, ""
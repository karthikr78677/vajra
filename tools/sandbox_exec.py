import subprocess
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

# Commands that require user permission before execution
PERMISSION_REQUIRED_COMMANDS = [
    "pip install", "conda install", "apt-get install", "apt install",
    "npm install", "npm i", "yarn add",
    "rm -rf", "rmdir", "del /f",
    "mkfs", "format",
    "python -m venv", "virtualenv",
]

# Maximum output characters before truncation
MAX_OUTPUT_CHARS = 2000


def _check_permission_required(code: str) -> str | None:
    """Returns the matched dangerous command if found, else None."""
    code_lower = code.lower()
    for cmd in PERMISSION_REQUIRED_COMMANDS:
        if cmd in code_lower:
            return cmd
    return None


def execute_code(code: str, interpreter: str = "python", timeout: int = 10, cwd: str | None = None, bypass_permission: bool = False) -> str:
    """
    Executes code in a restricted subprocess sandbox for various languages.

    Permission Rules:
    - If the code contains dangerous commands (pip install, rm -rf, etc.),
      returns PERMISSION_REQUIRED immediately WITHOUT executing.
    - The orchestrator/agent is responsible for pausing and asking the user.

    Args:
        code: Source code string to execute.
        interpreter: Language interpreter (python, node, bash, powershell).
        timeout: Max execution time in seconds.
        cwd: Current Working Directory to execute the code in.

    Returns:
        Output string, or PERMISSION_REQUIRED:... prefix if blocked.
    """
    logger.info(f"Sandbox: received code for '{interpreter}', timeout={timeout}s, cwd={cwd}")

    # 1. SECURITY CHECK: Block dangerous commands BEFORE executing
    if not bypass_permission:
        matched_cmd = _check_permission_required(code)
        if matched_cmd:
            msg = (
                f"PERMISSION_REQUIRED: The code contains a restricted command: '{matched_cmd}'.\n"
                f"This requires explicit user approval before it can be executed.\n"
                f"Action needed: User must approve via the UI or /approve endpoint."
            )
            logger.warning(msg)
            return msg

    # 2. Determine file extension based on interpreter
    ext_map = {
        "python": ".py",
        "node": ".js",
        "javascript": ".js",
        "bash": ".sh",
        "sh": ".sh",
        "powershell": ".ps1",
    }
    suffix = ext_map.get(interpreter.lower(), ".py")

    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        # Always write source files as UTF-8 so the interpreter can
        # handle any Unicode the model produces (e.g. ÷, ×, °, emoji).
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            # Prepend a PEP-263 encoding declaration to Python scripts so
            # CPython's own parser never raises "Non-UTF-8 code" errors.
            if suffix == '.py' and not code.lstrip().startswith('# -*- coding'):
                f.write('# -*- coding: utf-8 -*-\n')
            f.write(code)

        try:
            # If cwd is not specified, it runs in the system default or current process dir
            result = subprocess.run(
                [interpreter, path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                cwd=cwd
            )
        except FileNotFoundError:
            if cwd and not os.path.exists(cwd):
                return f"Sandbox error: The working directory '{cwd}' does not exist. Please create it first."
            return f"Sandbox error: Interpreter '{interpreter}' not found. Ensure it is installed and in PATH."
        except OSError as e:
            return f"Sandbox OS error: {e}"
        except subprocess.TimeoutExpired:
            return f"Timeout Error: Code execution exceeded {timeout} seconds."

        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"

        if not output.strip():
            output = "Code executed successfully with no output."

        # 3. CONTEXT PROTECTION: Truncate massive outputs
        if len(output) > MAX_OUTPUT_CHARS:
            logger.warning(f"Output too large ({len(output)} chars). Truncating.")
            output = (
                output[:1000]
                + f"\n\n... [OUTPUT TRUNCATED — {len(output) - 2000} chars hidden] ...\n\n"
                + output[-1000:]
            )

        logger.info(f"Sandbox: execution complete. Return code: {result.returncode}")
        return output

    except subprocess.TimeoutExpired:
        return f"Error: Execution timed out after {timeout}s. Possible infinite loop detected."
    except Exception as e:
        logger.exception(f"Sandbox unexpected error: {e}")
        return f"Error: Unexpected sandbox failure: {e}"
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

import subprocess
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

def execute_python(code: str, timeout: int = 10) -> str:
    """
    Executes Python code in a restricted subprocess sandbox.
    Captures stdout and stderr, safely truncating massive outputs.
    """
    logger.info(f"Executing sandboxed python code, timeout={timeout}s")
    
    # 1. SECURITY: Block package installations requiring permission
    if any(cmd in code for cmd in ["pip install", "conda install", "apt-get install"]):
        error_msg = "PERMISSION DENIED: Installing packages requires explicit user permission."
        logger.warning(error_msg)
        return error_msg
    
    # Create a temporary python file
    fd, path = tempfile.mkstemp(suffix=".py", text=True)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(code)
            
        # Execute the file via subprocess
        result = subprocess.run(
            ["python", path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
            
        if not output.strip():
            output = "Code executed successfully with no output."
            
        # 2. CONTEXT PROTECTION: Truncate massive outputs
        MAX_CHARS = 2000
        if len(output) > MAX_CHARS:
            logger.warning(f"Output too large ({len(output)} chars). Truncating.")
            output = output[:1000] + "\n\n... [OUTPUT TRUNCATED] ...\n\n" + output[-1000:]
            
        logger.info(f"Execution complete. Return code: {result.returncode}")
        return output
        
    except subprocess.TimeoutExpired:
        error_msg = f"Execution timed out after {timeout} seconds. You might have an infinite loop."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error during sandboxed execution: {e}"
        logger.error(error_msg)
        return error_msg
    finally:
        # Clean up the temporary file
        try:
            os.remove(path)
        except OSError:
            pass

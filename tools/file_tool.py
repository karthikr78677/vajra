import os
import logging

logger = logging.getLogger(__name__)

def read_file(filepath: str) -> str:
    """Reads the content of a local file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Read {len(content)} characters from {filepath}")
        return content
    except Exception as e:
        error_msg = f"Error reading file {filepath}: {e}"
        logger.error(error_msg)
        return error_msg

def write_file(filepath: str, content: str) -> str:
    """Writes text content to a local file, creating directories if needed."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Wrote to {filepath}")
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        error_msg = f"Error writing file {filepath}: {e}"
        logger.error(error_msg)
        return error_msg

def delete_file(filepath: str) -> str:
    """Blocks deletion without explicit user permission."""
    error_msg = f"PERMISSION DENIED: Deleting '{filepath}' requires explicit user permission."
    logger.warning(error_msg)
    return error_msg

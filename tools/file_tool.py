"""
Secure File Tool for Vajra Agent
All file operations are sandboxed to the project workspace only.
Any attempt to read/write/delete outside the workspace is blocked.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Security: ALL file ops are restricted to this folder and its subfolders ──
# This is loaded from the env if available, otherwise defaults to the project root.
_WORKSPACE_ROOT = Path(os.getenv("VAJRA_WORKSPACE", r"C:\Users\HP\Downloads\vajra")).resolve()
logger.info(f"File tool workspace root: {_WORKSPACE_ROOT}")


def _resolve_safe_path(filepath: str, workspace: str | None = None) -> Path | None:
    """
    Resolves a filepath and checks it is inside the workspace root.
    Returns the resolved Path if safe, or None if it tries to escape.
    Blocks path traversal attacks like '../../etc/passwd'.
    """
    try:
        active_workspace = Path(workspace).resolve() if workspace else _WORKSPACE_ROOT
        # Resolve to absolute, following any symlinks
        resolved = Path(filepath).resolve()
        # Check it is inside the workspace
        resolved.relative_to(active_workspace)
        return resolved
    except ValueError:
        return None  # Path escapes the workspace


def read_file(filepath: str, workspace: str | None = None) -> str:
    """
    Reads the content of a file inside the Vajra workspace or dynamic workspace.
    Blocked if the path tries to access any folder outside the active project.
    """
    active_workspace = Path(workspace).resolve() if workspace else _WORKSPACE_ROOT
    safe_path = _resolve_safe_path(filepath, workspace)
    if safe_path is None:
        msg = (
            f"PERMISSION DENIED: Cannot read '{filepath}'. "
            f"File operations are restricted to the workspace: {active_workspace}"
        )
        logger.warning(msg)
        return msg

    try:
        if not safe_path.exists():
            return f"Error: File not found: {filepath}"
        if not safe_path.is_file():
            return f"Error: '{filepath}' is a directory, not a file."

        content = safe_path.read_text(encoding="utf-8")
        logger.info(f"Read {len(content)} characters from '{safe_path.name}'")
        return content

    except PermissionError:
        return f"Error: OS permission denied reading '{filepath}'."
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return f"Error reading file '{filepath}': {e}"


def write_file(filepath: str, content: str, workspace: str | None = None) -> str:
    """
    Writes text content to a file inside the Vajra workspace or dynamic workspace.
    Creates parent directories if needed.
    Blocked if the path tries to access any folder outside the active project.
    """
    active_workspace = Path(workspace).resolve() if workspace else _WORKSPACE_ROOT
    # Resolve the path for checking, even if file doesn't exist yet
    try:
        resolved = (Path(filepath) if Path(filepath).is_absolute() else active_workspace / filepath).resolve()
        resolved.relative_to(active_workspace)
    except ValueError:
        msg = (
            f"PERMISSION DENIED: Cannot write to '{filepath}'. "
            f"File operations are restricted to the workspace: {active_workspace}"
        )
        logger.warning(msg)
        return msg

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        logger.info(f"Wrote {len(content)} characters to '{resolved.name}'")
        return f"Successfully wrote to '{resolved}'"

    except PermissionError:
        return f"Error: OS permission denied writing to '{filepath}'."
    except Exception as e:
        logger.error(f"Error writing file {filepath}: {e}")
        return f"Error writing file '{filepath}': {e}"


def delete_file(filepath: str, workspace: str | None = None) -> str:
    """
    Deletion always requires explicit user permission via the UI.
    Even if the file is inside the workspace, this is blocked at the tool level.
    The user must approve via the /approve endpoint after reviewing the request.
    """
    active_workspace = Path(workspace).resolve() if workspace else _WORKSPACE_ROOT
    safe_path = _resolve_safe_path(filepath, workspace)
    if safe_path is None:
        msg = (
            f"PERMISSION DENIED: Cannot delete '{filepath}'. "
            f"Path is outside the workspace: {active_workspace}"
        )
        logger.warning(msg)
        return msg

    # Even for in-workspace files, deletion requires explicit approval
    msg = (
        f"PERMISSION_REQUIRED: Deleting '{safe_path}' requires explicit user approval. "
        f"Please confirm via the UI Approve/Deny popup."
    )
    logger.warning(msg)
    return msg

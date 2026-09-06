"""
Permission Manager for Vajra Agent
Handles pausing execution and waiting for user approval on dangerous operations.
"""
import asyncio
import logging
import uuid
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PendingPermission:
    """Represents a single pending permission request."""
    def __init__(self, task_id: str, action: str, details: str):
        self.task_id = task_id
        self.action = action       # e.g. "pip install requests"
        self.details = details     # human-readable explanation
        self.event = asyncio.Event()  # Agent waits on this
        self.approved: Optional[bool] = None  # Set by user


class PermissionManager:
    """
    Singleton-style manager that:
    1. Receives permission requests from the sandbox/tools
    2. Pauses the agent (asyncio Event)
    3. Lets the UI/API resume with approve/deny
    """
    def __init__(self):
        self._pending: Dict[str, PendingPermission] = {}

    def request_permission(self, action: str, details: str) -> str:
        """
        Create a new permission request and return its task_id.
        The agent calls this and then awaits wait_for_decision().
        """
        task_id = str(uuid.uuid4())[:8]
        self._pending[task_id] = PendingPermission(task_id, action, details)
        logger.warning(f"PERMISSION REQUIRED [{task_id}]: {action}")
        return task_id

    async def wait_for_decision(self, task_id: str, timeout: float = 120.0) -> bool:
        """
        Blocks the agent coroutine until the user approves or denies,
        or until the timeout expires (default 2 minutes → auto-deny).
        """
        pending = self._pending.get(task_id)
        if not pending:
            return False

        logger.info(f"Agent paused. Waiting for user decision on [{task_id}]...")
        try:
            await asyncio.wait_for(pending.event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Permission request [{task_id}] timed out. Auto-denied.")
            pending.approved = False

        result = pending.approved or False
        del self._pending[task_id]
        return result

    def resolve(self, task_id: str, approved: bool):
        """Called by the API endpoint when the user clicks Approve/Deny."""
        pending = self._pending.get(task_id)
        if pending:
            pending.approved = approved
            pending.event.set()  # Unblocks the waiting agent
            logger.info(f"Permission [{task_id}] {'APPROVED' if approved else 'DENIED'} by user.")
        else:
            logger.warning(f"No pending permission found for task_id: {task_id}")

    def get_pending(self, task_id: str) -> Optional[PendingPermission]:
        return self._pending.get(task_id)

    def list_pending(self) -> Dict[str, dict]:
        return {
            tid: {"action": p.action, "details": p.details}
            for tid, p in self._pending.items()
        }


# Global singleton used by both the sandbox and the API
permission_manager = PermissionManager()

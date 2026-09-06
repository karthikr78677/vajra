"""
Interactive Test for Vajra Reasoning Agent (Scenario A / Vision)
Lets you test the Vision, OCR, and general tool-calling loop interactively.
Run: python -m tests.test_reasoning_interactive
"""

import asyncio
import logging
from backend.router import ModelRouter
from backend.schemas import TaskType
from agents.orchestrator import AgentOrchestrator
from agents.permission_manager import permission_manager

# Suppress INFO logs so the terminal is cleaner for the user
logging.getLogger("agents.orchestrator").setLevel(logging.WARNING)
logging.getLogger("backend.router").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def simulate_user_approval(task_id: str, action: str, details: str):
    """Simulates a popup asking the user for permission in the terminal."""
    print(f"\n==================================================")
    print(f"⚠️ PERMISSION REQUIRED")
    print(f"==================================================")
    print(f"Action : {action}")
    print(f"Details: {details.strip()}")
    print(f"--------------------------------------------------")
    
    while True:
        choice = input("Approve this action? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            print("→ APPROVED.")
            permission_manager.resolve(task_id, approved=True)
            break
        elif choice in ['n', 'no']:
            print("→ DENIED.")
            permission_manager.resolve(task_id, approved=False)
            break
        else:
            print("Please type 'y' or 'n'.")

async def monitor_permissions():
    """Background task to watch for permission requests and prompt the user."""
    while True:
        pending = permission_manager.list_pending()
        for task_id, info in pending.items():
            if not getattr(permission_manager.get_pending(task_id), '_asked', False):
                permission_manager.get_pending(task_id)._asked = True
                asyncio.create_task(simulate_user_approval(task_id, info['action'], info['details']))
        await asyncio.sleep(0.5)

async def main():
    print("=" * 60)
    print("  Vajra Reasoning Agent (Vision & OCR) Interactive Test")
    print("=" * 60)
    print("Type a request to test the agent's tool calling (Vision, File reading, etc).")
    print("Example: 'What is inside the image C:\\path\\to\\image.jpg?'")
    print("Type 'exit' to quit.\n")

    router = ModelRouter()
    orchestrator = AgentOrchestrator(router)
    
    # Start the background permission monitor
    perm_task = asyncio.create_task(monitor_permissions())

    while True:
        try:
            query = input("\nEnter query > ").strip()
            if not query:
                continue
            if query.lower() == 'exit':
                break

            print("\n[Agent is working...]")
            
            # Run the reasoning task
            output, trace = await orchestrator.run_async(query, TaskType.REASONING)
            
            print("\n================ FINAL OUTPUT ================")
            print(output)
            print("==============================================")
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n[Error] {e}")

    perm_task.cancel()
    await router.close()

if __name__ == "__main__":
    asyncio.run(main())

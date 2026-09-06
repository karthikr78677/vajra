"""
Interactive Test for Vajra Coding Agent (Scenario B)
Lets you test the dynamic workspace and coding loop interactively.
Run: python -m tests.test_coding_interactive
"""

import asyncio
import logging
from backend.router import ModelRouter
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
            # Only ask once per task
            if not getattr(permission_manager.get_pending(task_id), '_asked', False):
                permission_manager.get_pending(task_id)._asked = True
                asyncio.create_task(simulate_user_approval(task_id, info['action'], info['details']))
        await asyncio.sleep(0.5)

async def main():
    print("=" * 60)
    print("  Vajra Coding Agent Interactive Test")
    print("=" * 60)
    print("Type a coding request. To test dynamic workspaces, include a path!")
    print("Example: 'Write a python script in C:\\temp\\vajra_test to print Hello World'")
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
            
            # Run the coding task
            output, trace = await orchestrator.run_coding_task_async(query)
            
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

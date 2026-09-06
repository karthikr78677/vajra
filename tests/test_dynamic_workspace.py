import asyncio
import os
import shutil
import tempfile
import logging
from backend.router import ModelRouter
from agents.orchestrator import AgentOrchestrator

logging.basicConfig(level=logging.INFO)

async def test_dynamic_workspace():
    # Create a temporary directory that acts as the user's "local folder"
    test_dir = tempfile.mkdtemp(prefix="vajra_dynamic_ws_")
    print(f"\n--- Testing Dynamic Workspace Detection ---")
    print(f"Target test directory: {test_dir}\n")

    query = f"Write a Python script that creates a file named 'hello.txt' with the text 'Vajra Dynamic WS' in {test_dir}"
    
    router = ModelRouter()
    orchestrator = AgentOrchestrator(router)

    # We manually trigger the coding loop as it bypasses the normal task router for testing
    output, trace = await orchestrator.run_coding_task_async(query)

    print("\n--- Output ---")
    print(output.replace('✅', 'SUCCESS:').replace('❌', 'FAIL:').replace('⚠️', 'WARN:'))

    # Verify that the file was created in the correct dynamic workspace
    hello_file_path = os.path.join(test_dir, "hello.txt")
    if os.path.exists(hello_file_path):
        with open(hello_file_path, "r") as f:
            content = f.read()
        print(f"\n[PASS] File successfully created in dynamic workspace: {hello_file_path}")
        print(f"[PASS] File content: {content}")
    else:
        print(f"\n[FAIL] File was NOT created in dynamic workspace: {hello_file_path}")
        print("Checking if it was created in the current directory...")
        if os.path.exists("hello.txt"):
            print("[FAIL] File was created in the current working directory instead.")
            os.remove("hello.txt")

    # Cleanup
    shutil.rmtree(test_dir)
    await router.close()

if __name__ == "__main__":
    asyncio.run(test_dynamic_workspace())

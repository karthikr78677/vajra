import asyncio
from backend.router import ModelRouter
from backend.schemas import TaskType
from agents.orchestrator import AgentOrchestrator
import os

async def main():
    router = ModelRouter()
    orch = AgentOrchestrator(router)
    
    # Setup mock workspace
    ws_path = os.path.abspath("C:/Users/HP/Downloads/vajra-test/time")
    os.makedirs(ws_path, exist_ok=True)
    for f in ["index.html", "style.css", "script.js"]:
        with open(os.path.join(ws_path, f), "w") as fp:
            fp.write(f"// mockup of {f}")
            
    print("--- Test 1: Add new file to existing workspace ---")
    q1 = f"add settings.html to {ws_path}"
    print(f"Query: {q1}")
    extracted = orch._extract_workspace(q1)
    print(f"Extracted Workspace: {extracted}")
    target, query = orch._detect_edit_intent(q1, extracted)
    print(f"Edit target: {target}") # Should be None because settings.html is named but doesn't exist

    print("\n--- Test 2: Create wins over edit ---")
    q2 = f"create a todo app in {ws_path} with index.html, style.css"
    print(f"Query: {q2}")
    extracted2 = orch._extract_workspace(q2)
    target2, query2 = orch._detect_edit_intent(q2, extracted2)
    print(f"Edit target: {target2}") # Should be None because of "create" keyword

    print("\n--- Test 3: Edit existing project ---")
    q3 = f"fix the timer app in {ws_path}"
    print(f"Query: {q3}")
    extracted3 = orch._extract_workspace(q3)
    target3, query3 = orch._detect_edit_intent(q3, extracted3)
    print(f"Edit target: {target3}") # Should be a list of 3 files
    
    print("\n--- Test 4: Workspace extraction with spaces ---")
    q4 = "fix bug in \"C:/Users/HP/Downloads/My Apps/Project\""
    extracted4 = orch._extract_workspace(q4)
    print(f"Extracted Workspace: {extracted4}") # Should handle space
    
    print("\n--- Test 5: Route 'solve syntax error' ---")
    from tests.test_interactive import _llm_route_task
    task_type = await _llm_route_task(router, "solve syntax error in my app")
    print(f"Task Type: {task_type}")

if __name__ == "__main__":
    asyncio.run(main())

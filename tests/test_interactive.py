"""
Unified Interactive Test for the Vajra Agent System.
Supports all task types: REASONING, CODING, and VISION.
Run: python -m tests.test_interactive

Mode prefixes (optional - auto-detection used if omitted):
  [r] or [reasoning] : Force Reasoning mode (JSON tool-calling loop)
  [c] or [coding]    : Force Coding mode (code generation + sandbox)
  [v] or [vision]    : Force Vision/OCR mode (image analysis)

Or just type your query and Vajra will auto-detect the best mode.
Type 'help' to see usage, 'exit' or 'quit' to stop.
"""

import asyncio
import logging
import re
from backend.router import ModelRouter
from backend.schemas import TaskType
from agents.orchestrator import AgentOrchestrator
from agents.permission_manager import permission_manager

logging.getLogger("agents.orchestrator").setLevel(logging.WARNING)
logging.getLogger("backend.router").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

BANNER = """
+==============================================================+
|              Vajra  --  Unified Interactive Test             |
|         REASONING  |  CODING  |  VISION (OCR)               |
+==============================================================+
"""

HELP_TEXT = """
Mode prefixes (optional -- auto-detection used if omitted):
  [r]  or  [reasoning]  ->  JSON reasoning + tool-calling loop
  [c]  or  [coding]     ->  Code-generation + sandbox execution
  [v]  or  [vision]     ->  Image / PDF OCR and analysis

Examples:
  Write a calculator in C:\\temp\\calc
  [c] Build a Snake game in C:\\Users\\HP\\Desktop\\snake
  [r] What files are in C:\\Users\\HP\\Documents\\report.pdf?
  [v] What is in C:\\Users\\HP\\Pictures\\diagram.png?

Commands:
  help   -- show this guide
  exit   -- quit the program
"""

MODE_MAP = {
    "r": TaskType.REASONING,
    "reasoning": TaskType.REASONING,
    "c": TaskType.CODING,
    "coding": TaskType.CODING,
    "v": TaskType.VISION,
    "vision": TaskType.VISION,
}

_CODING_PATTERNS = re.compile(
    r"\b(write|create|generate|build|make|code|script|program|implement|develop)\b.*"
    r"\b(py|python|js|javascript|html|css|bash|script|function|class|app|game|tool|website|webpage)\b",
    re.IGNORECASE,
)
_VISION_PATTERNS = re.compile(
    r"\b(image|photo|picture|png|jpg|jpeg|pdf|ocr|scan|diagram|chart|screenshot|what is in|extract text)\b",
    re.IGNORECASE,
)

def _auto_detect(query):
    if _VISION_PATTERNS.search(query):
        return TaskType.VISION
    if _CODING_PATTERNS.search(query):
        return TaskType.CODING
    return TaskType.REASONING

def _parse_query(raw):
    m = re.match(r"^\[([a-zA-Z]+)\]\s*", raw.strip())
    if m:
        key = m.group(1).lower()
        task_type = MODE_MAP.get(key)
        if task_type:
            clean = raw[m.end():].strip()
            return task_type, clean
    return _auto_detect(raw), raw.strip()

_TASK_LABELS = {
    TaskType.REASONING: "REASONING  [thinking]",
    TaskType.CODING:    "CODING     [code]",
    TaskType.VISION:    "VISION     [image]",
}

async def _simulate_approval(task_id, action, details):
    print("\n" + "="*54)
    print("WARNING: PERMISSION REQUIRED")
    print("="*54)
    print(f"Action : {action}")
    print(f"Details: {details.strip()}")
    print("-"*54)
    while True:
        choice = input("Approve this action? (y/n): ").strip().lower()
        if choice in ("y", "yes"):
            print("-> APPROVED.")
            permission_manager.resolve(task_id, approved=True)
            break
        elif choice in ("n", "no"):
            print("-> DENIED.")
            permission_manager.resolve(task_id, approved=False)
            break
        else:
            print("Please type y or n.")

async def _monitor_permissions():
    while True:
        pending = permission_manager.list_pending()
        for task_id, info in pending.items():
            req = permission_manager.get_pending(task_id)
            if req and not getattr(req, "_asked", False):
                req._asked = True
                asyncio.create_task(_simulate_approval(task_id, info["action"], info["details"]))
        await asyncio.sleep(0.5)

async def main():
    print(BANNER)
    print(HELP_TEXT)
    router = ModelRouter()
    orchestrator = AgentOrchestrator(router)
    perm_task = asyncio.create_task(_monitor_permissions())
    try:
        while True:
            try:
                raw = input("vajra> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break
            if not raw:
                continue
            if raw.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            if raw.lower() == "help":
                print(HELP_TEXT)
                continue
            task_type, query = _parse_query(raw)
            label = _TASK_LABELS[task_type]
            print(f"\n[Mode: {label}]  Agent is working...\n")
            try:
                if task_type == TaskType.CODING:
                    output, trace = await orchestrator.run_coding_task_async(query)
                else:
                    output, trace = await orchestrator.run_async(query, task_type)
            except Exception as e:
                print(f"\n[Error] {e}")
                continue
            print("\n" + "="*54)
            print("  FINAL OUTPUT")
            print("="*54)
            print(output)
            print("="*54 + "\n")
            if trace:
                show = input("Show agent trace? (y/n): ").strip().lower()
                if show in ("y", "yes"):
                    print(f"\n--- Agent Trace ({len(trace)} steps) ---")
                    for i, step in enumerate(trace, 1):
                        print(f"\nStep {i}: [{step.action}]")
                        if step.thought:
                            print(f"  Thought    : {step.thought[:120]}")
                        print(f"  Observation: {step.observation[:200]}")
                    print("--- End of Trace ---\n")
    finally:
        perm_task.cancel()
        try:
            await router.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

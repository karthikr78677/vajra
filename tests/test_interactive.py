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

# ── LLM-based task router ──────────────────────────────────────────────────────
# Instead of brittle keyword matching, we ask the reasoning model to classify
# the intent in a single word. This correctly handles:
#   "fix the bug in script.js"     -> CODING
#   "add a dark theme to style.css" -> CODING
#   "what is in this image"        -> VISION
#   "summarise this PDF"           -> VISION
#   "explain how recursion works"  -> REASONING

_ROUTE_SYSTEM = (
    "You are a task router for an AI assistant called Vajra. "
    "Classify the user's query into exactly ONE of these three categories:\n"
    "  CODING  - write, create, generate, build, fix, edit, update, add, remove, "
    "change, modify, debug, refactor, improve code, scripts, HTML, CSS, JS, Python files.\n"
    "  VISION  - analyse, describe, extract text from, read an image, photo, PNG, JPG, "
    "screenshot, PDF, scan, diagram, chart, OCR.\n"
    "  REASONING - answer questions, explain concepts, summarise text, do maths, "
    "list files, search documents, anything not fitting CODING or VISION.\n"
    "Reply with ONLY the single word: CODING, VISION, or REASONING. Nothing else."
)

async def _llm_route_task(router: ModelRouter, query: str) -> TaskType:
    """
    Calls the reasoning model to classify the query.
    Falls back to a fast regex heuristic if the model is unresponsive.
    """
    # Fast heuristic fallback (used if LLM call fails)
    import re as _re
    _img_ext = _re.compile(r'\.(png|jpg|jpeg|bmp|tiff|webp|pdf)\b', _re.IGNORECASE)
    _file_ext = _re.compile(
        r'\b(\w+\.(html|css|js|ts|py|sh|json|md|txt))\b', _re.IGNORECASE
    )
    _edit_kw = _re.compile(
        r'\b(fix|change|update|modify|add|remove|build|create|generate|'
        r'write|make|code|refactor|debug|improve|style|extend)\b', _re.IGNORECASE
    )

    def _heuristic(q: str) -> TaskType:
        if _img_ext.search(q):
            return TaskType.VISION
        if _file_ext.search(q) or _edit_kw.search(q):
            return TaskType.CODING
        return TaskType.REASONING

    try:
        model = router.get_model_for_task(TaskType.REASONING)
        messages = [
            {"role": "system", "content": _ROUTE_SYSTEM},
            {"role": "user", "content": query}
        ]
        response = await router.chat_async(model, messages)
        word = response.strip().upper().split()[0] if response.strip() else ""
        if "VISION" in word:
            return TaskType.VISION
        if "CODING" in word or "CODE" in word:
            return TaskType.CODING
        if "REASON" in word:
            return TaskType.REASONING
        # If the model returned something unexpected, fall back to heuristic
        return _heuristic(query)
    except Exception:
        return _heuristic(query)


def _parse_query(raw: str):
    """Parses explicit [mode] prefix only. LLM routing handled separately in main."""
    m = re.match(r"^\[([a-zA-Z]+)\]\s*", raw.strip())
    if m:
        key = m.group(1).lower()
        task_type = MODE_MAP.get(key)
        if task_type:
            clean = raw[m.end():].strip()
            return task_type, clean
    return None, raw.strip()  # None = let LLM decide

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
                # Auto-approve in interactive test to prevent terminal noise
                permission_manager.resolve(task_id, approved=True)
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

            # If no explicit [mode] prefix, ask the LLM to classify the intent
            if task_type is None:
                print("  🔀 Routing...", end="", flush=True)
                task_type = await _llm_route_task(router, query)
                print(f"\r", end="", flush=True)  # clear the routing line

            # Auto-register any workspace path found in the query so the
            # permission manager allows file ops outside the default vajra dir
            import re as _re
            _ws_match = _re.search(r'([a-zA-Z]:[\\/][^\s\'",]+)', query)
            if _ws_match:
                ws_path = _ws_match.group(1).strip()
                import os as _os
                if _os.path.sep in ws_path or "/" in ws_path:
                    parent = _os.path.dirname(ws_path) if not _os.path.isdir(ws_path) else ws_path
                    try:
                        permission_manager.register_workspace(parent)
                    except Exception:
                        pass  # permission_manager may not have this method — safe to skip

            label = _TASK_LABELS[task_type]
            print(f"\n[Mode: {label}]  Agent is working...\n")
            try:
                output, trace = await orchestrator.run_async(query, task_type)
            except Exception as e:
                print(f"\n[Error] {e}")
                continue
            print("\n" + "="*54)
            print("  FINAL OUTPUT")
            print("="*54)
            print(_deduplicate_output(output))
            print("="*54 + "\n")
            if trace:
                try:
                    show = input("Show agent trace? (y/n): ").strip().lower()
                except EOFError:
                    show = "n"
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
        # Swallow ALL cleanup errors — they are all benign asyncio socket teardowns
        try:
            await asyncio.wait_for(router.close(), timeout=2.0)
        except Exception:
            pass

def _deduplicate_output(text: str, sentence_threshold: int = 3) -> str:
    """
    Detects when a vision/LLM model repeats the same sentence more than
    `sentence_threshold` times and truncates the output cleanly.
    """
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= sentence_threshold:
        return text
    seen: dict[str, int] = {}
    result = []
    for s in sentences:
        key = s.strip().lower()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > sentence_threshold:
            result.append("\n[Note: Repetitive output truncated]")
            break
        result.append(s)
    return " ".join(result)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass  # clean exit, no traceback

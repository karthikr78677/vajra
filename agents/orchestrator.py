import json
import logging
import re
from typing import List, Tuple
from backend.schemas import TaskType, AgentStep
from backend.router import ModelRouter
from tools.file_tool import read_file, write_file, delete_file
from tools.calculator_tool import calculate
from tools.sandbox_exec import execute_code
from tools.vision_tool import extract_text, get_document_info
from agents.permission_manager import permission_manager

logger = logging.getLogger(__name__)

# General Purpose Prompt (Reasoning)
REASONING_SYSTEM_PROMPT = """You are an AI Assistant that solves problems using tools.
You operate in a loop: THOUGHT -> ACTION -> OBSERVATION.

Available tools:
1. "read_file": {"filepath": "<path>"} - Reads a local file.
2. "write_file": {"filepath": "<path>", "content": "<text>"} - Writes to a local file.
3. "delete_file": {"filepath": "<path>"} - Deletes a local file.
4. "calculate": {"expression": "<math expression>"} - Evaluates math safely.
5. "execute_code": {"code": "<code string>", "interpreter": "<python|node|bash>"} - Runs code in a sandbox.
6. "extract_text": {"filepath": "<path>", "lang": "eng"} - Extracts text from a PDF or image (supports OCR on scanned PDFs).
7. "get_document_info": {"filepath": "<path>"} - Returns metadata (title, author, page count) of a PDF.

If you have the final answer or deliverable ready, use the tool "final_answer": {"text": "<your response>"}.
If a tool returns PERMISSION_REQUIRED, immediately use final_answer to ask the user for approval.
    
Format your output EXACTLY as valid JSON:
{
    "thought": "Your reasoning here...",
    "tool": "tool_name",
    "tool_input": {"key": "value"}
}
Do not add any other text outside this JSON block.
"""

# Specialized Coding Prompt (Scenario B)
# The 1.5B model cannot reliably output JSON, so we use a simpler
# "write code only" prompt and extract the code block with regex.
CODING_SYSTEM_PROMPT = """You are an Expert Software Engineer.
Your ONLY job is to write complete, working code to solve the user's request.

Rules:
- Write code in ANY language the user asks for (Python, JavaScript, Bash, etc.).
- ALWAYS wrap your code in a markdown code block with the language name.
- Example:
```python
print("Hello World")
```
- Do NOT use pip install or npm install — it is not permitted.
- Write only the code. Do not explain it.
"""

class AgentOrchestrator:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.max_retries = 8

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            if tool_name == "read_file":
                return read_file(tool_input.get("filepath", ""))
            elif tool_name == "write_file":
                return write_file(tool_input.get("filepath", ""), tool_input.get("content", ""))
            elif tool_name == "delete_file":
                return delete_file(tool_input.get("filepath", ""))
            elif tool_name == "calculate":
                return calculate(tool_input.get("expression", ""))
            elif tool_name == "execute_code":
                return execute_code(tool_input.get("code", ""), tool_input.get("interpreter", "python"))
            elif tool_name == "extract_text":
                return extract_text(tool_input.get("filepath", ""), tool_input.get("lang", "eng"))
            elif tool_name == "get_document_info":
                return get_document_info(tool_input.get("filepath", ""))
            else:
                return f"Error: Unknown tool {tool_name}"
        except Exception as e:
            return f"Error executing tool {tool_name}: {e}"

    async def run_coding_task_async(self, query: str) -> Tuple[str, List[AgentStep]]:
        """
        Specialized loop for coding tasks using the 1.5B coder model.
        Instead of JSON tool-calling (which the small model fails at),
        this loop simply asks the model to write code in a markdown block,
        extracts it with regex, runs it in the sandbox, and returns the result.
        Supports up to 3 fix iterations if the code crashes.
        """
        model_name = self.router.get_model_for_task(TaskType.CODING)
        logger.info(f"Coding Agent starting task with model '{model_name}'")

        # Extract target workspace path from the query (e.g. C:\path\to\folder)
        workspace = None
        path_match = re.search(r'([a-zA-Z]:[\\/][^\s\'",]+)', query)
        if path_match:
            workspace = path_match.group(1).strip()
            logger.info(f"Dynamically identified workspace: {workspace}")

        sys_prompt = CODING_SYSTEM_PROMPT
        if workspace:
            sys_prompt += f"\n- VERY IMPORTANT: The user wants to work in the directory: {workspace}\n- Assume this is your current working directory. You can read/write files relative to this directory, or use absolute paths within it.\n"

        trace = []
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": query}
        ]

        MAX_FIX_ATTEMPTS = 3
        for attempt in range(MAX_FIX_ATTEMPTS):
            logger.info(f"Coding Agent Attempt {attempt + 1}/{MAX_FIX_ATTEMPTS}")

            response_text = await self.router.chat_async(model_name, messages)

            # 1. Extract code block using regex (handles ```python, ```js, ```bash etc.)
            code_match = re.search(r"```(?:\w+)?\n(.*?)```", response_text, re.DOTALL)
            if not code_match:
                # Try to find any code-like content as fallback
                logger.warning("No markdown code block found. Retrying with correction.")
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": "Please wrap your code in a markdown code block like ```python ... ```"})
                continue

            code = code_match.group(1).strip()

            # 2. Detect interpreter from fence tag
            lang_match = re.search(r"```(\w+)", response_text)
            interpreter = "python"  # default
            if lang_match:
                lang = lang_match.group(1).lower()
                if lang in ("js", "javascript", "node"):
                    interpreter = "node"
                elif lang in ("bash", "sh", "shell", "powershell", "ps", "cmd"):
                    import os
                    interpreter = "powershell" if os.name == "nt" else "bash"

            thought = f"Generated {interpreter} code (attempt {attempt+1}). Running in sandbox to verify."
            logger.info(f"Extracted {interpreter} code ({len(code)} chars). Executing...")

            # 3. Run in sandbox
            output = execute_code(code, interpreter=interpreter, cwd=workspace)

            # 4. Check for permission blocks — PAUSE and wait for user
            if "PERMISSION_REQUIRED" in output:
                task_id = permission_manager.request_permission(
                    action=f"Execute {interpreter} code",
                    details=output
                )
                trace.append(AgentStep(
                    thought=thought,
                    action="execute_code",
                    action_input={"code": code, "interpreter": interpreter},
                    observation=output
                ))
                logger.info(f"Agent PAUSED. Waiting for user approval [task_id={task_id}]...")
                approved = await permission_manager.wait_for_decision(task_id, timeout=120.0)

                if not approved:
                    return f"❌ Action denied by user (or timed out after 2 minutes). Execution cancelled.", trace

                # User approved — re-run the code now
                logger.info(f"User APPROVED [{task_id}]. Re-executing code...")
                output = execute_code(code, interpreter=interpreter, cwd=workspace, bypass_permission=True)

            # 5. Check if code ran successfully (no obvious error markers)
            has_error = any(marker in output for marker in ["Traceback", "Error:", "SyntaxError", "NameError", "TypeError"])
            trace.append(AgentStep(thought=thought, action="execute_code",
                                   action_input={"code": code, "interpreter": interpreter},
                                   observation=output))

            if not has_error:
                # SUCCESS — Return code + output
                final = f"✅ Code generated and verified successfully!\n\n```{interpreter}\n{code}\n```\n\n**Output:**\n```\n{output}\n```"
                return final, trace
            else:
                # Code crashed — send error back to model for auto-fix
                logger.warning(f"Code execution failed. Sending error to model for auto-fix.")
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Your code failed with this error:\n{output}\n\nFix the bug and rewrite the complete code."})

        return "❌ Could not generate working code after 3 attempts. Please refine your request.", trace

    async def run_async(self, query: str, task_type: TaskType) -> Tuple[str, List[AgentStep]]:
        """
        Main entry point. Routes CODING tasks to the specialized coding loop,
        and all other tasks to the general JSON tool-calling loop.
        """
        # Route coding tasks to the specialized loop
        if task_type == TaskType.CODING:
            return await self.run_coding_task_async(query)

        model_name = self.router.get_model_for_task(task_type)
        logger.info(f"Orchestrator starting task '{query}' with model '{model_name}'")

        sys_prompt = REASONING_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": query}
        ]

        trace = []
        action_history = []

        for iteration in range(self.max_retries):
            logger.info(f"Agent Loop Iteration {iteration + 1}/{self.max_retries}")

            response_text = await self.router.chat_async(model_name, messages)

            # Robust JSON extraction
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            json_str = match.group(0) if match else response_text

            try:
                parsed = json.loads(json_str)
                thought = parsed.get("thought", "")
                tool_name = parsed.get("tool", "")
                tool_input = parsed.get("tool_input", {})

                if tool_name == "final_answer":
                    final_text = tool_input.get("text", str(tool_input))
                    trace.append(AgentStep(thought=thought, action="final_answer", action_input=tool_input, observation="Task Complete"))
                    return final_text, trace

                # Loop breaking
                current_action = f"{tool_name}:{str(tool_input)}"
                action_history.append(current_action)

                if action_history.count(current_action) >= 3:
                    observation = "SYSTEM WARNING: You are stuck in a loop repeating the same action. Stop repeating. Try a completely different approach or use the final_answer tool."
                else:
                    observation = self._execute_tool(tool_name, tool_input)

                trace.append(AgentStep(
                    thought=thought,
                    action=tool_name,
                    action_input=tool_input,
                    observation=observation
                ))

                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Observation from {tool_name}: {observation}\nNow continue."})

            except json.JSONDecodeError:
                logger.warning("Agent produced invalid JSON. Retrying.")
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": "Error: Output was not valid JSON. Please extract only the JSON object."})

        return "Max retries reached without final answer.", trace

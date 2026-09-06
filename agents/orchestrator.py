import json
import logging
import re
from typing import List, Tuple
from backend.schemas import TaskType, AgentStep
from backend.router import ModelRouter
from tools.file_tool import read_file, write_file, delete_file
from tools.calculator_tool import calculate
from tools.sandbox_exec import execute_code
from tools.vision_tool import extract_text, get_document_info, analyze_image
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
8. "analyze_image": {"filepath": "<path>", "question": "<question>"} - Analyzes a photo, schematic, or engineering drawing.

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

# ── Coding Prompt ──────────────────────────────────────────────────────────────
# The small 1.5B model cannot reliably output JSON, so the coding loop
# extracts markdown code blocks via regex and runs them in the sandbox.
CODING_SYSTEM_PROMPT = """You are an Elite Senior Software Engineer with 20+ years of experience.
Your job: write COMPLETE, PRODUCTION-QUALITY, BEAUTIFUL code.

STRICT RULES — violating any rule = task failure:
1. ALWAYS wrap code in a markdown code block with the language name: ```python ... ```
2. NEVER write placeholder comments like "# add more here" or "<!-- TODO -->".
   Every function, button, style rule, and feature must be FULLY IMPLEMENTED.
3. For UI (HTML/CSS/JS): use modern design — dark theme, gradients, smooth animations,
   Google Fonts, glassmorphism, hover effects, transitions. NO plain grey boxes.
4. For Python scripts that CREATE files: embed the COMPLETE file contents as multiline
   strings. Do NOT leave HTML/CSS/JS content empty or with placeholders.
5. Code must run on first try. No syntax errors. No missing dependencies.
6. Write only the code block. No explanations before or after.
"""

# Per-file focused prompt — used in the multi-file pipeline.
# Injected once per file so the model only thinks about ONE file at a time.
FILE_CONTENT_PROMPT_TEMPLATE = """You are an Elite Frontend/Backend Engineer.
Write ONLY the complete, production-ready content for the file: {filename}

Project context:
{project_context}

{previously_generated_files}

Design requirements for this file:
{design_requirements}

RULES:
- Output ONLY the raw file content inside a single ```{lang} ... ``` block.
- ZERO placeholders. ZERO TODO comments. EVERY line must be real, working code.
- For CSS: use variables, animations, transitions, modern layout (grid/flex).
- For JS: all functions must be fully implemented and working.
- For HTML: every button, input, and element must be wired up.
"""


class AgentOrchestrator:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.max_retries = 8

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _detect_multifile_task(self, query: str) -> list:
        """
        Detects if the user query asks for named files.
        Returns a list of filenames (e.g. ['index.html', 'style.css']).
        Returns an empty list if no explicit filenames are found.
        """
        pattern = re.compile(
            r"['\"]?([\w\-]+\.(?:html|css|js|ts|py|sh|json|md|txt|jsx|tsx|vue|scss|sass))['\"]?",
            re.IGNORECASE,
        )
        found = list(dict.fromkeys(m.group(1) for m in pattern.finditer(query)))
        # Return the list if ANY files are detected (1 or more)
        return found if len(found) >= 1 else []

    def _extract_workspace(self, query: str):
        """Extracts an absolute directory path from the query."""
        m = re.search(r'([a-zA-Z]:[\\/][^\s\'",]+)', query)
        return m.group(1).strip() if m else None

    async def _generate_file_content(
        self, model_name: str, filename: str, lang: str,
        project_context: str, design_requirements: str,
        previously_generated_files: str = "",
    ) -> str:
        """
        Calls the model to generate raw content for a SINGLE file.
        Returns the extracted code string, or empty string on failure.
        """
        sys_prompt = FILE_CONTENT_PROMPT_TEMPLATE.format(
            filename=filename, lang=lang,
            project_context=project_context,
            design_requirements=design_requirements,
            previously_generated_files=previously_generated_files,
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Write the complete content for: {filename}"},
        ]
        for _ in range(3):
            response = await self.router.chat_async(model_name, messages)
            match = re.search(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL)
            if match:
                return match.group(1).strip()
            lines = response.strip().splitlines()
            if len(lines) > 2:
                return "\n".join(lines).strip()
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Wrap your code in a ```{lang} ... ``` block."})
        return ""

    def _get_design_requirements(self, filename: str, query: str) -> tuple:
        """Returns (lang, design_requirements) for a given filename."""
        lower = filename.lower()
        if lower.endswith(".html"):
            return "html", (
                "Create a COMPLETE HTML structure with ALL interactive elements fully wired. "
                "Use semantic HTML5. Link to style.css and script.js. "
                "Import Google Fonts in <head>. Every button/input must have correct onclick/onchange attributes. "
                "No placeholders. The page must look premium when opened in a browser."
            )
        elif lower.endswith(".css"):
            return "css", (
                "Create stunning, modern CSS. MUST include: "
                "CSS custom properties (variables) for the full color palette, "
                "dark color scheme (e.g. #0d1117, #161b22), gradient backgrounds, "
                "glassmorphism for card/container elements (backdrop-filter: blur), "
                "smooth transitions (0.2-0.3s ease) on ALL interactive elements, "
                "hover and :active states on all buttons, "
                "CSS Grid or Flexbox layouts, Google Font @import at top, "
                "box-shadow and border-radius for depth, keyframe animations. "
                "Make it look like a premium app — WOW factor is required."
            )
        elif lower.endswith(".js"):
            return "js", (
                "Write complete, fully working JavaScript. Every function must be implemented end-to-end. "
                "Use modern ES6+ (const, let, arrow functions, template literals, destructuring). "
                "Add keyboard event listeners, smooth DOM manipulation, and error handling. "
                "No placeholder comments. All features must work correctly."
            )
        elif lower.endswith(".py"):
            return "python", (
                "Write complete Python. All functions implemented. "
                "Use pathlib for file operations. Handle errors with try/except. "
                "Create directories with mkdir(parents=True, exist_ok=True)."
            )
        else:
            lang = lower.rsplit(".", 1)[-1] if "." in lower else "text"
            return lang, "Write complete, working content. No placeholders."

    # ── Multi-file pipeline ────────────────────────────────────────────────────

    async def run_multifile_coding_async(
        self, query: str, filenames: list, workspace: str
    ) -> tuple:
        """
        Generates multiple files ONE AT A TIME in focused model calls.
        Each file gets a targeted prompt so the model never runs out of context.
        Files are written directly via write_file (no sandbox needed).
        This produces complete, beautiful output that the sandbox loop cannot.
        """
        import os as _os
        model_name = self.router.get_model_for_task(TaskType.CODING)
        logger.info(f"Multi-file pipeline: {filenames} -> workspace: {workspace}")

        project_context = (
            f"Project goal: {query}\n"
            f"Files to create: {', '.join(filenames)}\n"
            f"Output directory: {workspace}\n"
            f"These files work TOGETHER as one complete, beautiful project."
        )

        trace: List[AgentStep] = []
        created_files: list = []
        failed_files: list = []
        previously_generated: dict[str, str] = {}

        for filename in filenames:
            lang, design_req = self._get_design_requirements(filename, query)
            logger.info(f"Generating {filename} ({lang})...")
            print(f"  → Generating {filename}...", flush=True)

            # Build context from previously generated files to ensure IDs/classes match
            prev_files_context = ""
            if previously_generated:
                prev_files_context = "Previously generated files you must integrate with:\n\n"
                for prev_name, prev_content in previously_generated.items():
                    prev_files_context += f"--- {prev_name} ---\n```{prev_content}```\n\n"

            content = await self._generate_file_content(
                model_name=model_name,
                filename=filename,
                lang=lang,
                project_context=project_context,
                design_requirements=design_req,
                previously_generated_files=prev_files_context,
            )

            if not content:
                logger.warning(f"Failed to generate content for {filename}")
                failed_files.append(filename)
                trace.append(AgentStep(
                    thought=f"Attempting to generate {filename}",
                    action="write_file",
                    action_input={"filepath": _os.path.join(workspace, filename)},
                    observation=f"FAILED: Model returned empty content for {filename}"
                ))
                continue

            # Save content so the next file can reference it
            previously_generated[filename] = content

            filepath = _os.path.join(workspace, filename)
            result = write_file(filepath, content, workspace=workspace)
            created_files.append(filepath)
            logger.info(f"Wrote {filename}: {result}")

            trace.append(AgentStep(
                thought=f"Generated complete {lang} content for {filename} ({len(content)} chars)",
                action="write_file",
                action_input={"filepath": filepath},
                observation=result,
            ))

        lines = []
        if created_files:
            lines.append(f"✅ Successfully created {len(created_files)} file(s):")
            for f in created_files:
                lines.append(f"   • {f}")
        if failed_files:
            lines.append(f"\n⚠️  Failed to generate {len(failed_files)} file(s): {', '.join(failed_files)}")
        if created_files:
            lines.append(f"\nOpen '{_os.path.join(workspace, filenames[0])}' in your browser to see the result.")

        return "\n".join(lines), trace

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
            elif tool_name == "analyze_image":
                return analyze_image(tool_input.get("filepath", ""), tool_input.get("question", ""))
            else:
                return f"Error: Unknown tool {tool_name}"
        except Exception as e:
            return f"Error executing tool {tool_name}: {e}"

    async def run_coding_task_async(self, query: str) -> Tuple[str, List[AgentStep]]:
        """
        Main coding entry point. Automatically chooses the best strategy:
        - Multi-file pipeline: when query mentions 2+ named files AND a workspace path.
          Generates each file in a separate focused model call → writes directly.
          Produces complete, beautiful output the sandbox loop cannot match.
        - Single-file sandbox loop: fallback for single-file or script tasks.
          Generates code, runs it in the sandbox, auto-fixes errors up to 3x.
        """
        model_name = self.router.get_model_for_task(TaskType.CODING)
        logger.info(f"Coding Agent starting task with model '{model_name}'")

        workspace = self._extract_workspace(query)
        filenames = self._detect_multifile_task(query)

        # ── Strategy A: Multi-file pipeline ────────────────────────────────────
        if filenames and workspace:
            logger.info(f"Routing to multi-file pipeline: {filenames}")
            return await self.run_multifile_coding_async(query, filenames, workspace)

        # ── Strategy B: Single-file sandbox loop ───────────────────────────────
        logger.info("Routing to single-file sandbox loop")
        workspace = workspace  # may be None

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

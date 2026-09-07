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
REASONING_SYSTEM_PROMPT = """You are VAJRA, an offline AI assistant. You have NO internet access whatsoever.

CRITICAL RULES - follow these exactly:
1. INTERNET IS BLOCKED. Never use requests, urllib, BeautifulSoup, httpx, or any network library.
2. GENERAL KNOWLEDGE QUESTIONS (who is X, what is Y, explain Z, history, sports, science, math facts):
   Answer IMMEDIATELY using "final_answer" from your own training knowledge. Use NO other tool.
3. Tools exist ONLY for: local file operations, local calculations, local code, or local KB search.
4. Output ONLY a single valid JSON object. Zero text outside it.

HOW TO DECIDE:
- "Who is X" / "What is Y" / "Explain Z" / "Describe X" -> final_answer from own knowledge NOW.
- "Read file at C:\path" -> read_file tool.
- "Calculate 2+2" -> calculate tool.
- "Run this code" -> execute_code tool (no internet inside sandbox either).
- "What does our SOP say about X" -> search_knowledge_base tool.

Available tools:
1. "read_file": {"filepath": "<absolute path>"} - Read a local file.
2. "write_file": {"filepath": "<absolute path>", "content": "<text>"} - Write a local file.
3. "delete_file": {"filepath": "<absolute path>"} - Delete a local file.
4. "calculate": {"expression": "<expression>"} - Evaluate math safely.
5. "execute_code": {"code": "<code>", "interpreter": "python"} - Run local code (no internet).
6. "extract_text": {"filepath": "<path>", "lang": "eng"} - Extract text from a local PDF/image.
7. "get_document_info": {"filepath": "<path>"} - Get metadata of a local PDF.
8. "analyze_image": {"filepath": "<path>", "question": "<q>"} - Analyse a local image.
9. "search_knowledge_base": {"query": "<query>"} - Search local company SOPs/manuals.
10. "final_answer": {"text": "<your full answer>"} - Return final answer to user.

Output format (ONLY this, nothing else):
{
    "thought": "one or two sentence reasoning about what to do",
    "tool": "tool_name",
    "tool_input": {"key": "value"}
}

EXAMPLE - general knowledge question:
User asks: "who is MS Dhoni?"
You output:
{
    "thought": "This is a general knowledge question. I will answer directly from my training knowledge.",
    "tool": "final_answer",
    "tool_input": {"text": "MS Dhoni (Mahendra Singh Dhoni) is a legendary Indian cricketer and former captain of the Indian national cricket team. Born on July 7, 1981, in Ranchi, India, he is widely regarded as one of the greatest wicket-keeper batsmen and finishers in cricket history. He led India to three ICC tournament victories: 2007 ICC World Twenty20, 2011 ICC Cricket World Cup, and 2013 ICC Champions Trophy. Known for his calm temperament under pressure, he earned the nickname Captain Cool."}
}
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
        import re as _re
        # Try matching paths in quotes (handles spaces perfectly)
        m = _re.search(r'["\']([a-zA-Z]:[\\/][^"\']+)["\']', query)
        if m:
            return m.group(1).strip()
        # Fallback for unquoted paths — stop at common query separators and accidental terminal chars
        m = _re.search(r'([a-zA-Z]:[\\/][^\n,;><\?\*]+?(?=\s+(?:with|and|—|-|$)))', query, _re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Final fallback (no spaces allowed)
        m = _re.search(r'([a-zA-Z]:[\\/][^\s\'",><\?\*]+)', query)
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

    # ── Feature 2: Smart AST-Based Context Compression ────────────────────────

    def _extract_file_structure(self, filename: str, content: str) -> str:
        """
        Extracts a compact structural summary from a generated file.
        Instead of passing the full raw content (expensive — thousands of tokens)
        to the next model call, we extract only the skeleton that the next file
        needs to know about: IDs, class names, function names, CSS variables, etc.

        Token savings: typically 90%+ reduction vs. full file dump.
        This keeps the model's context window free for actual generation.
        """
        lower = filename.lower()
        lines = []

        try:
            if lower.endswith(".html"):
                # Extract IDs, classes, event handlers, form inputs
                ids = re.findall(r'id=["\']([^"\']+)["\']', content)
                classes = re.findall(r'class=["\']([^"\']+)["\']', content)
                onclicks = re.findall(r'onclick=["\']([^"\']+)["\']', content)
                inputs = re.findall(r'<input[^>]*name=["\']([^"\']+)["\']', content)
                # Flatten multi-class strings into individual class names
                all_classes = list(dict.fromkeys(
                    c for group in classes for c in group.split()
                ))
                if ids:
                    lines.append(f"IDs: {', '.join(dict.fromkeys(ids))}")
                if all_classes:
                    lines.append(f"Classes: {', '.join(all_classes[:20])}")
                if onclicks:
                    lines.append(f"onclick handlers: {', '.join(dict.fromkeys(onclicks))}")
                if inputs:
                    lines.append(f"Form inputs (name): {', '.join(inputs)}")

            elif lower.endswith(".css"):
                # Extract CSS custom properties and class/id selectors
                css_vars = re.findall(r'(--[\w-]+)\s*:', content)
                selectors = re.findall(r'^([.#][\w][\w\s,.-]*?)\s*\{', content, re.MULTILINE)
                if css_vars:
                    lines.append(f"CSS variables: {', '.join(dict.fromkeys(css_vars))}")
                if selectors:
                    clean = [s.strip() for s in selectors[:25]]
                    lines.append(f"Selectors: {', '.join(clean)}")

            elif lower.endswith(".js") or lower.endswith(".ts"):
                # Extract function/const/let declarations and event listeners
                funcs = re.findall(
                    r'(?:function\s+([\w]+)|(?:const|let|var)\s+([\w]+)\s*=\s*(?:async\s*)?(?:function|\())',
                    content
                )
                func_names = [f[0] or f[1] for f in funcs if any(f)]
                listeners = re.findall(r'addEventListener\(["\']([\w]+)["\']', content)
                exports = re.findall(r'export\s+(?:default\s+)?(?:function|class|const)\s+([\w]+)', content)
                if func_names:
                    lines.append(f"Functions/vars: {', '.join(dict.fromkeys(func_names))}")
                if listeners:
                    lines.append(f"Event listeners: {', '.join(dict.fromkeys(listeners))}")
                if exports:
                    lines.append(f"Exports: {', '.join(exports)}")

            elif lower.endswith(".py"):
                # Use Python's built-in AST for perfect accuracy
                import ast as _ast
                try:
                    tree = _ast.parse(content)
                    imports = []
                    funcs = []
                    classes = []
                    for node in _ast.walk(tree):
                        if isinstance(node, (_ast.Import, _ast.ImportFrom)):
                            if isinstance(node, _ast.ImportFrom):
                                imports.append(f"{node.module}")
                            else:
                                imports.extend(a.name for a in node.names)
                        elif isinstance(node, _ast.FunctionDef):
                            args = [a.arg for a in node.args.args]
                            funcs.append(f"{node.name}({', '.join(args)})")
                        elif isinstance(node, _ast.ClassDef):
                            classes.append(node.name)
                    if imports:
                        lines.append(f"Imports: {', '.join(dict.fromkeys(imports))}")
                    if classes:
                        lines.append(f"Classes: {', '.join(classes)}")
                    if funcs:
                        lines.append(f"Functions: {'; '.join(funcs[:20])}")
                except SyntaxError:
                    # Fallback: simple regex if AST parse fails
                    funcs = re.findall(r'^def ([\w]+)\(', content, re.MULTILINE)
                    lines.append(f"Functions: {', '.join(funcs)}")

            elif lower.endswith(".json"):
                # Just show top-level keys
                import json as _json
                try:
                    data = _json.loads(content)
                    if isinstance(data, dict):
                        lines.append(f"Top-level keys: {', '.join(list(data.keys())[:20])}")
                except Exception:
                    lines.append("(JSON file — structure unavailable)")

        except Exception as e:
            logger.debug(f"Structure extraction failed for {filename}: {e}")
            # Safe fallback: return first 300 chars only
            return f"(structure extraction failed — first 300 chars):\n{content[:300]}"

        if not lines:
            return f"(no significant structure detected in {filename})"

        return "\n".join(lines)

    # ── Feature 1: Edit / Fix Mode ─────────────────────────────────────────────

    _EDIT_KEYWORDS = re.compile(
        r'\b(fix|solve|repair|patch|clean|sanitize|lint|optimize|format|refine|'
        r'revamp|rework|change|update|modify|refactor|add|remove|delete|replace|rename|'
        r'improve|enhance|debug|correct|adjust|rewrite|extend|style|color|font|'
        r'move|align|resize|convert|make|turn|set|reduce|increase|decrease|'
        r'resolve|address|handle|correct|overhaul|migrate|upgrade|port)\b',
        re.IGNORECASE
    )

    def _detect_edit_intent(self, query: str, workspace: str) -> tuple:
        """
        Detects if the user wants to EDIT an existing file rather than create a new one.

        Returns (target_filepath, instruction) if edit intent is found, else (None, None).

        Edit intent = edit keyword + a filename that ALREADY EXISTS in workspace.
        """
        import os as _os

        if not workspace:
            return None, None

        # Supported editable extensions
        EDITABLE_EXTS = {
            ".html", ".css", ".js", ".ts", ".py", ".sh",
            ".json", ".md", ".txt", ".jsx", ".tsx", ".vue", ".scss", ".sass"
        }

        # Find any filename explicitly mentioned in the query
        file_pattern = re.compile(
            r"['\"]?([\w\-]+\.(?:html|css|js|ts|py|sh|json|md|txt|jsx|tsx|vue|scss|sass))['\"]?",
            re.IGNORECASE
        )
        mentioned_files = [m.group(1) for m in file_pattern.finditer(query)]

        has_edit_keyword = bool(self._EDIT_KEYWORDS.search(query))
        has_create_keyword = bool(re.search(r'\b(create|build|generate|write|make)\b', query, re.IGNORECASE))

        # Ambiguity fix: if user explicitly asked to CREATE specific files, DO NOT
        # fall into edit mode. (This prevents "style.css" from triggering the "style" edit keyword).
        if has_create_keyword and mentioned_files:
            return None, None

        # Case 1: Specific file(s) mentioned AND edit keyword present
        if has_edit_keyword and mentioned_files:
            # Ambiguity fix: if user says "add style.css to ...", and style.css doesn't exist, it's creation!
            # We only return it as an edit target if it actually exists.
            found_any = False
            for fname in mentioned_files:
                candidate = _os.path.join(workspace, fname)
                if _os.path.isfile(candidate):
                    logger.info(f"Edit mode (named file): target='{candidate}'")
                    return candidate, query
                    
            # If we reached here, they named specific files but NONE exist yet!
            # This means it's a request to CREATE those files in the existing dir.
            return None, None

        # Case 2: Workspace directory EXISTS on disk (with or without explicit keyword).
        # If the LLM already classified this as CODING and the workspace has code files,
        # it MUST be an edit task — scan and return all files.
        if _os.path.isdir(workspace):
            found = [
                _os.path.join(workspace, f)
                for f in sorted(_os.listdir(workspace))
                if _os.path.splitext(f)[1].lower() in EDITABLE_EXTS
                and _os.path.isfile(_os.path.join(workspace, f))
            ]
            if found:
                logger.info(f"Edit mode (workspace scan): {len(found)} file(s) in '{workspace}'")
                return found, query  # list = multi-file edit

        return None, None

    async def run_edit_task_async(
        self, query: str, target_filepath: str
    ) -> tuple:
        """
        Targeted file editor. Reads the current file content, sends it to the
        model with the user's instruction, and overwrites only that file.

        Uses the CODING model. Preserves all parts of the file not mentioned
        in the edit instruction — it does NOT regenerate from scratch.
        """
        import os as _os
        model_name = self.router.get_model_for_task(TaskType.CODING)
        filename = _os.path.basename(target_filepath)
        workspace = _os.path.dirname(target_filepath)
        lang, _ = self._get_design_requirements(filename, query)

        logger.info(f"Edit mode: editing '{filename}' in '{workspace}'")
        print(f"  ✏️  Editing existing file: {filename}...", flush=True)

        # Read the existing file — pass workspace so permission check uses the right root
        current_content = read_file(target_filepath, workspace=workspace)
        if current_content.startswith("Error") or current_content.startswith("PERMISSION"):
            return f"❌ Could not read '{filename}': {current_content}", []

        edit_prompt = (
            f"You are editing an existing {lang} file called '{filename}'.\n"
            f"User's instruction: {query}\n\n"
            f"Here is the CURRENT content of {filename}:\n"
            f"```{lang}\n{current_content}\n```\n\n"
            f"Make ONLY the changes described in the instruction. "
            f"Return the COMPLETE updated file in a ```{lang} ... ``` block. "
            f"Do not remove any unrelated parts. No placeholders."
        )

        messages = [
            {"role": "system", "content": (
                f"You are an expert {lang} developer. "
                f"Edit files precisely. Return only the updated file inside a code block."
            )},
            {"role": "user", "content": edit_prompt}
        ]

        new_content = ""
        for attempt in range(3):
            response = await self.router.chat_async(model_name, messages)
            match = re.search(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL)
            if match:
                new_content = match.group(1).strip()
                break
            lines = response.strip().splitlines()
            if len(lines) > 3:
                new_content = "\n".join(lines).strip()
                break
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Wrap the complete updated {filename} in a ```{lang} ... ``` block."})

        if not new_content:
            return f"❌ Model failed to return updated content for '{filename}'.", []

        result = write_file(target_filepath, new_content, workspace=workspace)

        trace = [AgentStep(
            thought=f"Edit instruction: '{query[:100]}'. Read existing {filename} ({len(current_content)} chars), applied changes, wrote {len(new_content)} chars.",
            action="write_file",
            action_input={"filepath": target_filepath},
            observation=result
        )]

        final = (
            f"✅ Successfully edited '{filename}'\n"
            f"   File: {target_filepath}\n"
            f"   Original: {len(current_content)} chars → Updated: {len(new_content)} chars\n"
            f"   Change: {query[:120]}"
        )
        return final, trace


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

            # Build COMPACT structural summary from previously generated files
            # (replaces raw file dump — saves ~90% tokens while retaining all
            # the information the next model needs: IDs, functions, CSS vars etc.)
            prev_files_context = ""
            if previously_generated:
                prev_files_context = (
                    "Previously generated files — structural summary "
                    "(use these exact IDs/classes/functions to integrate):\n\n"
                )
                for prev_name, prev_content in previously_generated.items():
                    structure = self._extract_file_structure(prev_name, prev_content)
                    prev_files_context += f"### {prev_name}\n{structure}\n\n"

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

        # ── Strategy A: Edit existing file(s) ──────────────────────────────────
        # Checked BEFORE multi-file to avoid re-generating existing projects.
        # _detect_edit_intent returns either:
        #   str  -> single file path (named explicitly in query)
        #   list -> all files in workspace dir (no specific file named)
        if workspace:
            edit_target, instruction = self._detect_edit_intent(query, workspace)
            if edit_target:
                # Single file edit
                if isinstance(edit_target, str):
                    logger.info(f"Routing to Edit Mode (single): '{edit_target}'")
                    return await self.run_edit_task_async(instruction, edit_target)

                # Multi-file edit (whole project fix)
                if isinstance(edit_target, list):
                    logger.info(f"Routing to Edit Mode (project): {len(edit_target)} files")
                    print(f"  🔍 Found {len(edit_target)} file(s) in project. Planning targeted edits...", flush=True)
                    
                    import os as _os
                    import re as _re

                    # Step 1: Read structural summaries of the existing project
                    summaries = []
                    for fpath in edit_target:
                        content = read_file(fpath, workspace=workspace)
                        if content and not content.startswith("Error") and not content.startswith("PERMISSION"):
                            struct = self._extract_file_structure(_os.path.basename(fpath), content)
                            summaries.append(f"### {_os.path.basename(fpath)}\n{struct}")
                            
                    # Step 2: Use Reasoning model to PLAN the edit
                    planning_prompt = (
                        f"User instruction: {instruction}\n\n"
                        f"Current Project Structure:\n{chr(10).join(summaries)}\n\n"
                        "Which files need to be edited to complete this instruction?\n"
                        "For each file that MUST be changed, output a line in exactly this format:\n"
                        "EDIT_FILE: filename.ext | specific technical instruction for this file based on its structure\n\n"
                        "Only include files that actually require changes. Do not include files that don't need edits."
                    )
                    
                    plan_model = self.router.get_model_for_task(TaskType.REASONING)
                    messages = [{"role": "system", "content": "You are a senior developer planning targeted project edits."}, {"role": "user", "content": planning_prompt}]
                    plan_response = await self.router.chat_async(plan_model, messages)
                    
                    tasks = _re.findall(r"EDIT_FILE:\s*([\w\-\.]+)\s*\|\s*(.+)", plan_response)
                    
                    if not tasks:
                        # Fallback: if planning fails, apply edit to all files
                        logger.warning("Planning failed to yield EDIT_FILE targets, falling back to all")
                        tasks = [(_os.path.basename(f), instruction) for f in edit_target]
                        
                    print(f"  📋 Plan complete: editing {len(tasks)} file(s) based on structural analysis.", flush=True)
                    
                    # Step 3: Execute the targeted edits
                    all_trace = []
                    edited_files = []
                    for fname, spec_instr in tasks:
                        fpath = _os.path.join(workspace, fname)
                        if fpath in edit_target:
                            out, tr = await self.run_edit_task_async(f"{instruction}\n\n(Specific focus for this file: {spec_instr})", fpath)
                            edited_files.append(fname)
                            all_trace.extend(tr)
                            
                    summary = (
                        f"✅ Applied targeted fixes to {len(edited_files)} file(s):\n"
                        + "\n".join(f"   • {p}" for p in edited_files)
                        + f"\n\nInstruction applied: {instruction[:120]}"
                    )
                    return summary, all_trace

        # ── Strategy B: Multi-file pipeline (create new project) ───────────────
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

    async def run_vision_task_async(self, query: str) -> Tuple[str, List[AgentStep]]:
        """
        Dedicated vision handler. Directly calls the vision tool without going
        through the JSON reasoning loop (which always fails for vision tasks).

        Strategy:
        - Extracts file path from the query using regex.
        - If image (.png/.jpg/.bmp etc): calls analyze_image() directly.
        - If PDF: calls extract_text() directly.
        - Returns the raw tool result as the final answer.
        """
        import os as _os

        # Extract a file path from the query (Windows or Unix style)
        path_match = re.search(
            r'"([^"]+\.(?:png|jpg|jpeg|bmp|tiff?|webp|pdf))"|'
            r"'([^']+\.(?:png|jpg|jpeg|bmp|tiff?|webp|pdf))'|"
            r'([a-zA-Z]:[\\/][^\s,;]+\.(?:png|jpg|jpeg|bmp|tiff?|webp|pdf))',
            query, re.IGNORECASE
        )

        if not path_match:
            answer = (
                "I could not find a valid file path in your request. "
                "Please include the full path to the image or PDF, for example:\n"
                "  Analyse C:\\Users\\HP\\Pictures\\photo.png"
            )
            trace = [AgentStep(
                thought="No file path found in query.",
                action="final_answer",
                action_input={"text": answer},
                observation="Task Complete"
            )]
            return answer, trace

        # Pick whichever capture group matched
        filepath = (path_match.group(1) or path_match.group(2) or path_match.group(3)).strip()
        filepath = filepath.strip('"').strip("'")
        ext = _os.path.splitext(filepath)[1].lower()

        logger.info(f"Vision task: file='{filepath}' ext='{ext}'")
        print(f"  → Analysing: {filepath}", flush=True)

        # Route to the right tool
        if ext == ".pdf":
            result = extract_text(filepath)
            action = "extract_text"
        else:
            # Detect OCR intent: "extract text", "ocr", "read text" etc. -> use Tesseract OCR
            ocr_intent = re.search(
                r'\b(extract text|ocr|read text|get text|text from|transcribe|text in)\b',
                query, re.IGNORECASE
            )
            if ocr_intent:
                result = extract_text(filepath)
                action = "extract_text"
            else:
                # Detect if user asks a specific question about the image
                question_match = re.search(
                    r'(?:what|describe|identify|find|analyse|analyze|tell me|explain)\s+(.+)',
                    query, re.IGNORECASE
                )
                question = question_match.group(0) if question_match else "Describe this image in detail."
                result = analyze_image(filepath, question=question)
                action = "analyze_image"
        trace = [AgentStep(
            thought=f"User asked about '{_os.path.basename(filepath)}'. Calling {action} directly.",
            action=action,
            action_input={"filepath": filepath},
            observation=result[:500] if result else "No result"
        )]

        if not result or result.startswith("Error"):
            final = f"⚠️ Vision tool returned: {result}"
        else:
            final = f"📄 **Analysis of `{_os.path.basename(filepath)}`:**\n\n{result}"

        return final, trace

    async def run_async(self, query: str, task_type: TaskType,
                        history: list = None, file_paths: list = None) -> Tuple[str, List[AgentStep]]:
        """
        Main entry point. Routes tasks to their specialized handlers:
        - CODING  → run_coding_task_async  (multi-file pipeline / sandbox)
        - VISION  → run_vision_task_async  (direct tool call, no JSON loop)
        - REASONING → general JSON tool-calling loop

        Args:
            query: Current user message.
            task_type: Classified task type.
            history: List of prior {role, content} dicts for multi-turn context.
            file_paths: Absolute paths of uploaded files to process.
        """
        # Enrich query with file context if files were provided
        if file_paths:
            file_list = ", ".join(file_paths)
            query = f"{query}\n\n[Attached files: {file_list}]"

        if task_type == TaskType.CODING:
            return await self.run_coding_task_async(query)

        # Route vision tasks to the dedicated direct handler
        if task_type == TaskType.VISION:
            return await self.run_vision_task_async(query)

        model_name = self.router.get_model_for_task(task_type)
        logger.info(f"Orchestrator starting task '{query[:80]}...' with model '{model_name}'")

        sys_prompt = REASONING_SYSTEM_PROMPT

        # Build messages: system → history turns → current user query
        messages = [{"role": "system", "content": sys_prompt}]

        if history:
            for h in history:
                role = h.get("role", "user") if isinstance(h, dict) else h.role
                content = h.get("content", "") if isinstance(h, dict) else h.content
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": query})

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


import json
import logging
import re
from typing import List, Tuple
from backend.schemas import TaskType, AgentStep
from backend.router import ModelRouter
from tools.file_tool import read_file, write_file, delete_file
from tools.calculator_tool import calculate
from tools.sandbox_exec import execute_python

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI Assistant that solves problems using tools.
You operate in a loop: THOUGHT -> ACTION -> OBSERVATION.

Available tools:
1. "read_file": {"filepath": "<path>"} - Reads a local file.
2. "write_file": {"filepath": "<path>", "content": "<text>"} - Writes to a local file.
3. "delete_file": {"filepath": "<path>"} - Deletes a local file.
4. "calculate": {"expression": "<math expression>"} - Evaluates math safely.
5. "execute_python": {"code": "<python code>"} - Runs Python code in a sandbox and returns output.

If you have the final answer or deliverable ready, use the tool "final_answer": {"text": "<your response>"}.

Format your output EXACTLY as valid JSON:
{
    "thought": "Your reasoning here...",
    "tool": "tool_name",
    "tool_input": {"key": "value"}
}
Do not add any other text outside this JSON block.
"""

class AgentOrchestrator:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.max_retries = 8  # Increased for complex tasks

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
            elif tool_name == "execute_python":
                return execute_python(tool_input.get("code", ""))
            else:
                return f"Error: Unknown tool {tool_name}"
        except Exception as e:
            return f"Error executing tool {tool_name}: {e}"

    async def run_async(self, query: str, task_type: TaskType) -> Tuple[str, List[AgentStep]]:
        """
        Runs the Plan -> Act -> Observe -> Retry loop asynchronously.
        Includes robust JSON extraction and loop-breaking capabilities.
        """
        model_name = self.router.get_model_for_task(task_type)
        logger.info(f"Orchestrator starting task '{query}' with model '{model_name}'")
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]
        
        trace = []
        action_history = []
        
        for iteration in range(self.max_retries):
            logger.info(f"Agent Loop Iteration {iteration + 1}/{self.max_retries}")
            
            response_text = await self.router.chat_async(model_name, messages)
            
            # 1. ROBUST JSON EXTRACTION
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
                
                # 2. LOOP BREAKING DETECTION
                current_action = f"{tool_name}:{str(tool_input)}"
                action_history.append(current_action)
                
                if action_history.count(current_action) >= 3:
                    observation = "SYSTEM WARNING: You are stuck in a loop repeating the same action. Stop repeating. Try a completely different approach or use the final_answer tool."
                    logger.warning("Agent stuck in a loop. Injected warning.")
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

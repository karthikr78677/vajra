import yaml
import httpx
import logging
import json
from typing import Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from backend.schemas import TaskType

logger = logging.getLogger(__name__)

class ModelRouter:
    def __init__(self, config_path: str = "models/router_config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
            
        self.base_url = self.config.get("ollama_base_url", "http://localhost:11434")
        self.models = self.config.get("models", {})
        
        # Async HTTP client with a reasonable timeout for LLM generation
        self.client = httpx.AsyncClient(timeout=120.0)
        
    def get_model_for_task(self, task_type: TaskType) -> str:
        """Returns the model name for the given task type."""
        mapping = {
            TaskType.REASONING: self.models.get("reasoning", {}).get("name", "qwen2.5:3b"),
            TaskType.CODING: self.models.get("coding", {}).get("name", "qwen2.5-coder:1.5b"),
            TaskType.VISION: self.models.get("vision", {}).get("name", "moondream:latest"),
        }
        return mapping.get(task_type, mapping[TaskType.REASONING])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(httpx.RequestError))
    async def generate_async(self, model_name: str, prompt: str, system: str = "", images: List[str] = None) -> str:
        """
        Sends an async generation request to Ollama with retry logic.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images
            
        logger.info(f"Routing async generate to model: {model_name}")
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(httpx.RequestError))
    async def chat_async(self, model_name: str, messages: List[Dict[str, Any]]) -> str:
        """
        Sends an async chat request to Ollama.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False
        }
        
        logger.info(f"Routing async chat to model: {model_name}")
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    async def chat_stream_async(self, model_name: str, messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        """
        Streams chat responses from Ollama as an async generator for SSE.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True
        }
        
        logger.info(f"Starting async streaming chat to model: {model_name}")
        
        async with self.client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode streaming JSON: {line}")
                        
    async def close(self):
        await self.client.aclose()

import re
import logging
from typing import List
from backend.schemas import UserRequest, TaskAnalysisResult, TaskType
from backend.router import ModelRouter

logger = logging.getLogger(__name__)

async def analyze_task_async(request: UserRequest, router: ModelRouter) -> TaskAnalysisResult:
    """
    Classifies a UserRequest using a hybrid approach:
    1. Fast heuristics (extensions, regex).
    2. Lightweight LLM call if heuristics are ambiguous.
    """
    query = request.query.lower()
    files = request.file_paths
    
    # Check for vision first (image files) - highly reliable heuristic
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    has_image = any(any(f.lower().endswith(ext) for ext in image_extensions) for f in files)
    
    if has_image:
        return TaskAnalysisResult(
            task_type=TaskType.VISION,
            reasoning="Image files detected in the request.",
            confidence_score=1.0,
            is_fallback=False
        )
        
    # Check for strong coding keywords
    coding_keywords = ["write a python script", "debug this code", "bash command", "execute"]
    if any(keyword in query for keyword in coding_keywords):
        return TaskAnalysisResult(
            task_type=TaskType.CODING,
            reasoning="Strong coding-related keywords found in the query.",
            confidence_score=0.9,
            is_fallback=False
        )
        
    # If it falls through, use LLM classification
    logger.info("Task intent ambiguous. Falling back to LLM classification.")
    prompt = f"Classify this user request into EXACTLY ONE of these categories: [REASONING, CODING, VISION]. Reply with only the category word.\n\nUser Request: '{request.query}'"
    
    try:
        model_name = router.get_model_for_task(TaskType.REASONING)
        llm_response = await router.generate_async(model_name, prompt)
        clean_resp = llm_response.strip().upper()
        
        if "CODING" in clean_resp:
            return TaskAnalysisResult(task_type=TaskType.CODING, reasoning=f"LLM classified as CODING", confidence_score=0.8, is_fallback=True)
        elif "VISION" in clean_resp:
            return TaskAnalysisResult(task_type=TaskType.VISION, reasoning=f"LLM classified as VISION", confidence_score=0.8, is_fallback=True)
        else:
            return TaskAnalysisResult(task_type=TaskType.REASONING, reasoning=f"LLM classified as REASONING", confidence_score=0.8, is_fallback=True)
            
    except Exception as e:
        logger.error(f"LLM classification failed: {e}. Hard defaulting to REASONING.")
        return TaskAnalysisResult(
            task_type=TaskType.REASONING,
            reasoning="Hard fallback to REASONING due to LLM error.",
            confidence_score=0.5,
            is_fallback=True
        )

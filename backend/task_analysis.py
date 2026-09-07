import re
import logging
from backend.schemas import UserRequest, TaskAnalysisResult, TaskType
from backend.router import ModelRouter

logger = logging.getLogger(__name__)

async def analyze_task_async(request: UserRequest, router: ModelRouter) -> TaskAnalysisResult:
    """
    Classifies a UserRequest using a hybrid approach:
    1. Fast heuristics (extensions, regex, keywords).
    2. Lightweight LLM call only if heuristics are ambiguous.
    """
    query = request.query.strip()
    query_lower = query.lower()
    files = request.file_paths

    # ── Priority 1: File-based VISION detection (100% reliable) ──────────────
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
    pdf_extensions   = {".pdf"}
    has_image = any(any(f.lower().endswith(ext) for ext in image_extensions) for f in files)
    has_pdf   = any(any(f.lower().endswith(ext) for ext in pdf_extensions)   for f in files)

    if has_image or has_pdf:
        return TaskAnalysisResult(
            task_type=TaskType.VISION,
            reasoning="Image or PDF files detected in the request.",
            confidence_score=1.0,
            is_fallback=False
        )

    # ── Priority 2: Strong REASONING keyword patterns ─────────────────────────
    # These catch general knowledge/Q&A questions the small LLM often misclassifies.
    reasoning_patterns = [
        r"^who (is|are|was|were)\b",
        r"^what (is|are|was|were)\b",
        r"^where (is|are|was|were)\b",
        r"^when (is|are|was|were|did|does|do)\b",
        r"^why (is|are|was|were|did|does|do)\b",
        r"^how (is|are|was|were|did|does|do|can|should|would|to)\b",
        r"^tell me (about|more)\b",
        r"^explain\b",
        r"^describe\b",
        r"^summarize\b",
        r"^compare\b",
        r"^define\b",
        r"^list\b",
        r"^give me\b",
    ]
    for pattern in reasoning_patterns:
        if re.match(pattern, query_lower):
            return TaskAnalysisResult(
                task_type=TaskType.REASONING,
                reasoning=f"General knowledge/analysis question matched pattern: '{pattern}'",
                confidence_score=0.95,
                is_fallback=False
            )

    # ── Priority 3: Explicit file path or OCR keyword → VISION ───────────────
    vision_path_pattern = re.search(
        r'[a-zA-Z]:[/\\].*\.(?:png|jpg|jpeg|bmp|tiff?|webp|pdf)\b',
        query_lower
    )
    vision_keywords = ["analyse this image", "analyze this image", "ocr this",
                       "extract text from", "read the pdf"]
    if vision_path_pattern or any(k in query_lower for k in vision_keywords):
        return TaskAnalysisResult(
            task_type=TaskType.VISION,
            reasoning="File path or explicit vision keyword in query.",
            confidence_score=0.95,
            is_fallback=False
        )

    # ── Priority 4: Strong CODING keyword patterns ────────────────────────────
    coding_patterns = [
        r"\b(write|create|build|generate|make)\b.{0,30}(script|code|program|app|function|class|algorithm|calculator|game|tool|bot)\b",
        r"\b(debug|fix|refactor|optimize)\b.{0,30}(code|script|error|bug|function)\b",
        r"\b(python|javascript|bash|powershell|typescript|c\+\+|java)\b.{0,30}\b(script|code|function|class)\b",
        r"\bwrite a python\b",
        r"\bwrite code\b",
        r"\bexecute (a |this )?(script|code|command|program)\b",
    ]
    for pattern in coding_patterns:
        if re.search(pattern, query_lower):
            return TaskAnalysisResult(
                task_type=TaskType.CODING,
                reasoning=f"Strong coding keyword matched: '{pattern}'",
                confidence_score=0.9,
                is_fallback=False
            )

    # ── Priority 5: LLM fallback (only for truly ambiguous queries) ───────────
    logger.info("Task intent ambiguous. Falling back to LLM classification.")
    prompt = (
        "Classify this user request into EXACTLY ONE category.\n"
        "Categories:\n"
        "  REASONING - general knowledge, questions, explanations, analysis, math\n"
        "  CODING    - writing code, scripts, programs, debugging\n"
        "  VISION    - analysing image files or PDF files at a given file path\n\n"
        f"User Request: '{request.query}'\n\n"
        "Reply with ONLY the category word (REASONING, CODING, or VISION). Nothing else."
    )

    try:
        model_name = router.get_model_for_task(TaskType.REASONING)
        llm_response = await router.generate_async(model_name, prompt)
        clean_resp = llm_response.strip().upper()

        if "CODING" in clean_resp:
            return TaskAnalysisResult(task_type=TaskType.CODING, reasoning="LLM classified as CODING", confidence_score=0.8, is_fallback=True)
        elif "VISION" in clean_resp:
            return TaskAnalysisResult(task_type=TaskType.VISION, reasoning="LLM classified as VISION", confidence_score=0.8, is_fallback=True)
        else:
            return TaskAnalysisResult(task_type=TaskType.REASONING, reasoning="LLM classified as REASONING", confidence_score=0.8, is_fallback=True)

    except Exception as e:
        logger.error(f"LLM classification failed: {e}. Hard defaulting to REASONING.")
        return TaskAnalysisResult(
            task_type=TaskType.REASONING,
            reasoning="Hard fallback to REASONING due to LLM error.",
            confidence_score=0.5,
            is_fallback=True
        )

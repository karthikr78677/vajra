import math
import logging

logger = logging.getLogger(__name__)

def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression safely.
    Uses eval with a restricted dictionary of mathematical functions.
    """
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    allowed_names.update({
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow
    })
    
    try:
        # Evaluate safely without builtins
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        logger.info(f"Calculated: {expression} = {result}")
        return str(result)
    except Exception as e:
        error_msg = f"Error evaluating expression '{expression}': {e}"
        logger.error(error_msg)
        return error_msg

"""Local multimodal vision analyzer for industrial drawings and photos.

Uses moondream via Ollama for sovereign, air-gapped visual reasoning.
"""

import base64
import io
import logging
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image

from backend.schemas import TaskType

logger = logging.getLogger(__name__)

# Supported image file extensions
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}

# Industrial Domain Prompt Presets
PROMPT_PRESETS = {
    "diagram": (
        "Analyze this engineering drawing / P&ID schematic in detail. "
        "Identify and extract:\n"
        "1. Title block and document metadata (if present).\n"
        "2. Tagged components, instruments, and equipment (e.g., valves, transmitters, vessels).\n"
        "3. Pipeline lines, line sizes, flow directions, and pressure/temperature ratings.\n"
        "4. Inspection notes, alert boxes, and maintenance actions."
    ),
    "inspection": (
        "Analyze this industrial equipment photo / inspection image. "
        "Identify and report:\n"
        "1. Equipment type and primary visible components.\n"
        "2. Observable physical conditions (corrosion, cracks, wear, leaks, loose connections).\n"
        "3. Severity assessment and recommended maintenance actions."
    ),
    "general": (
        "Describe this industrial image or drawing in detail, highlighting visible components, "
        "labels, measurements, and any anomalies."
    ),
}


def validate_and_load_image(image_path: str) -> Image.Image:
    """Validate that the file exists, has a supported format, and can be opened as an image."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: '{image_path}'")
    if not path.is_file():
        raise ValueError(f"Path is not a file: '{image_path}'")
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported image format '{path.suffix}'. Supported formats: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    try:
        img = Image.open(str(path))
        img.verify()  # verify integrity
        # Reopen because verify() closes the file pointer in Pillow
        img = Image.open(str(path))
        return img
    except Exception as e:
        raise ValueError(f"Corrupted or unreadable image file '{image_path}': {e}") from e


def encode_image_to_base64(image_path: str, max_dimension: int = 1024) -> str:
    """Read an image file, resize if dimensions exceed max_dimension, and return a base64 string."""
    img = validate_and_load_image(image_path)

    # Convert grayscale or RGBA to RGB for standard JPEG encoding
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Downscale large images while preserving aspect ratio to save VRAM and latency
    width, height = img.size
    if max(width, height) > max_dimension:
        scale = max_dimension / max(width, height)
        new_size = (int(width * scale), int(height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def build_vision_prompt(prompt: Optional[str] = None, task_preset: str = "general") -> str:
    """Construct the final prompt for the vision model based on user query and task preset."""
    if prompt and prompt.strip():
        user_query = prompt.strip()
        # If user gave a specific question, combine it with context
        return f"Examine this image carefully and answer the question:\n{user_query}"

    return PROMPT_PRESETS.get(task_preset.lower(), PROMPT_PRESETS["general"])


async def analyze_image_async(
    image_path: str,
    prompt: Optional[str] = None,
    router=None,
    task_preset: str = "general",
) -> str:
    """Analyze an image using moondream via Ollama asynchronously."""
    try:
        base64_image = encode_image_to_base64(image_path)
    except Exception as e:
        return f"Error loading image: {e}"

    final_prompt = build_vision_prompt(prompt, task_preset)

    if router is not None:
        model_name = router.get_model_for_task(TaskType.VISION)
        try:
            return await router.generate_async(
                model_name=model_name,
                prompt=final_prompt,
                images=[base64_image],
            )
        except Exception as e:
            return f"Error during vision model inference ({model_name}): {e}"

    # Fallback to direct local Ollama HTTP request if router not provided
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "moondream:latest",
        "prompt": final_prompt,
        "images": [base64_image],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
    except httpx.ConnectError:
        return "Error: Cannot connect to local Ollama server at http://localhost:11434. Ensure Ollama is running."
    except Exception as e:
        return f"Error in vision analysis: {e}"


def analyze_image(
    image_path: str,
    prompt: Optional[str] = None,
    router=None,
    task_preset: str = "general",
) -> str:
    """Synchronous wrapper for analyze_image, safe for calling from synchronous agent tools."""
    try:
        base64_image = encode_image_to_base64(image_path)
    except Exception as e:
        return f"Error loading image: {e}"

    final_prompt = build_vision_prompt(prompt, task_preset)
    base_url = router.base_url if router and hasattr(router, "base_url") else "http://localhost:11434"
    model_name = (
        router.get_model_for_task(TaskType.VISION)
        if router and hasattr(router, "get_model_for_task")
        else "moondream:latest"
    )

    url = f"{base_url}/api/generate"
    payload = {
        "model": model_name,
        "prompt": final_prompt,
        "images": [base64_image],
        "stream": False,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
    except httpx.ConnectError:
        return f"Error: Cannot connect to local Ollama server at {base_url}. Ensure Ollama is running."
    except Exception as e:
        return f"Error in vision analysis: {e}"

"""Vision Engine module matching Vajra folder structure specifications.

Wraps the local moondream model and exposes visual analysis APIs.
"""

from typing import Optional

from vision.analyzer import (
    PROMPT_PRESETS,
    SUPPORTED_IMAGE_EXTENSIONS,
    analyze_image,
    analyze_image_async,
    build_vision_prompt,
    encode_image_to_base64,
    validate_and_load_image,
)


class VisionEngine:
    """Object-oriented engine for air-gapped image and drawing analysis."""

    def __init__(self, router=None, default_preset: str = "general"):
        self.router = router
        self.default_preset = default_preset

    async def describe_image_async(self, image_path: str, question: Optional[str] = None) -> str:
        """Asynchronously analyze an image or drawing with an optional question."""
        return await analyze_image_async(
            image_path=image_path,
            prompt=question,
            router=self.router,
            task_preset=self.default_preset,
        )

    def describe_image(self, image_path: str, question: Optional[str] = None) -> str:
        """Synchronously analyze an image or drawing with an optional question."""
        return analyze_image(
            image_path=image_path,
            prompt=question,
            router=self.router,
            task_preset=self.default_preset,
        )


__all__ = [
    "VisionEngine",
    "analyze_image",
    "analyze_image_async",
    "build_vision_prompt",
    "encode_image_to_base64",
    "validate_and_load_image",
    "PROMPT_PRESETS",
    "SUPPORTED_IMAGE_EXTENSIONS",
]

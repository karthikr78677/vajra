"""Unified local document and image text extraction tool."""

from pathlib import Path

from ocr.engine import extract_text_from_image
from preprocessing.parser import extract_text_from_pdf


def extract_text(file_path: str) -> str:
    """Extract text from a supported local PDF or image file."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    if suffix in {".jpg", ".jpeg", ".png"}:
        return extract_text_from_image(file_path)
    return f"Error: Unsupported file type '{suffix or 'unknown'}'. Use PDF, JPG, or PNG."
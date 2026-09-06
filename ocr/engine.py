"""Local image OCR using Tesseract."""

import os
from pathlib import Path

import pytesseract
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

TESSERACT_CMD = os.getenv("TESSERACT_CMD")
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def extract_text_from_image(file_path: str) -> str:
    """Extract text from a local JPG or PNG, returning a clean error on failure."""
    path = Path(file_path)
    if not path.is_file():
        return f"Error: Image file not found: {file_path}"
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        return f"Error: Expected a JPG or PNG image: {file_path}"

    try:
        with Image.open(path) as image:
            return pytesseract.image_to_string(image)
    except (OSError, RuntimeError, pytesseract.TesseractError) as exc:
        return f"Error: Could not OCR image '{file_path}': {exc}"
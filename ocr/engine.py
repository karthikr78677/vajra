"""
Production-grade OCR engine using Tesseract.
Supports images (JPG, PNG, TIFF, BMP) and in-memory PyMuPDF pixmaps.
"""

import logging
import os
from pathlib import Path

import pytesseract
from dotenv import load_dotenv
from PIL import Image, ImageFilter, ImageOps
try:
    import pymupdf as fitz  # PyMuPDF >= 1.24
except ImportError:
    import fitz  # PyMuPDF < 1.24  # for Pixmap type hint

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Tesseract binary path from .env
TESSERACT_CMD = os.getenv("TESSERACT_CMD")
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    logger.info(f"Tesseract configured at: {TESSERACT_CMD}")
else:
    logger.warning("TESSERACT_CMD not set in .env — relying on system PATH.")

# Supported image formats
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

# Tesseract config: LSTM engine + auto page segmentation mode
TESSERACT_CONFIG = "--oem 1 --psm 3"

# Max image dimension for very large scans — resize to prevent memory exhaustion
MAX_IMAGE_DIMENSION = 5000


def _preprocess_image(image: Image.Image) -> Image.Image:
    """
    Apply production-level image preprocessing to maximize OCR accuracy.
    Steps: convert to grayscale -> auto-contrast -> sharpen -> deskew readiness.
    """
    # Convert to grayscale
    image = image.convert("L")
    # Auto-contrast to normalize brightness
    image = ImageOps.autocontrast(image, cutoff=1)
    # Sharpen to make characters crisper
    image = image.filter(ImageFilter.SHARPEN)
    # Resize if extremely large
    w, h = image.size
    if max(w, h) > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        logger.info(f"Downsampled large image to {image.size}")
    return image


def extract_text_from_image(file_path: str, lang: str = "eng") -> str:
    """
    Extract text from a local image file using Tesseract OCR.

    Args:
        file_path: Absolute path to the image file.
        lang: Tesseract language code (default 'eng'). Use 'eng+hin' for multilingual.

    Returns:
        Extracted text string, or a clean error message on failure.
    """
    path = Path(file_path)

    if not path.exists():
        return f"Error: Image file not found: {file_path}"
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        return (
            f"Error: Unsupported image format '{path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    logger.info(f"Running OCR on image: {file_path} (lang={lang})")

    try:
        with Image.open(path) as raw_image:
            processed = _preprocess_image(raw_image.copy())
            text = pytesseract.image_to_string(
                processed, lang=lang, config=TESSERACT_CONFIG
            ).strip()

        if not text:
            logger.warning(f"OCR returned empty result for: {file_path}")
            return "Warning: OCR completed but extracted no text. The image may be blank or unreadable."

        logger.info(f"OCR complete. Extracted {len(text)} characters from '{path.name}'.")
        return text

    except pytesseract.TesseractNotFoundError:
        return (
            "Error: Tesseract not found. Please install Tesseract and set TESSERACT_CMD "
            "in your .env file. See README.md for instructions."
        )
    except pytesseract.TesseractError as exc:
        return f"Error: Tesseract OCR failed for '{file_path}': {exc}"
    except (OSError, RuntimeError) as exc:
        return f"Error: Could not open image '{file_path}': {exc}"
    except Exception as exc:
        logger.exception(f"Unexpected OCR error: {exc}")
        return f"Error: Unexpected OCR failure on '{file_path}': {exc}"


def extract_text_from_pixmap(pix: fitz.Pixmap, lang: str = "eng") -> str:
    """
    Extract text from an in-memory PyMuPDF Pixmap (used for scanned PDF pages).
    Converts pixmap bytes directly to a PIL Image to avoid disk I/O.

    Args:
        pix: A fitz.Pixmap rendered from a PDF page.
        lang: Tesseract language code.

    Returns:
        Extracted text string, or a clean error message on failure.
    """
    logger.info(f"Running OCR on in-memory pixmap ({pix.width}x{pix.height}px, lang={lang})")

    try:
        # Convert PyMuPDF pixmap to PIL Image via raw bytes
        mode = "RGB" if pix.n == 3 else "RGBA"
        image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)

        processed = _preprocess_image(image)
        text = pytesseract.image_to_string(
            processed, lang=lang, config=TESSERACT_CONFIG
        ).strip()

        if not text:
            return "Warning: OCR on this page returned no text."

        logger.info(f"Pixmap OCR complete. Extracted {len(text)} characters.")
        return text

    except pytesseract.TesseractError as exc:
        return f"Error: Tesseract failed on rendered page: {exc}"
    except Exception as exc:
        logger.exception(f"Unexpected pixmap OCR error: {exc}")
        return f"Error: Unexpected failure during page OCR: {exc}"
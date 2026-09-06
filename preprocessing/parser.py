"""
Production-grade PDF text extraction for local documents.
Supports native text PDFs and falls back to OCR for scanned/image-based PDFs.
"""

import logging
from pathlib import Path
from typing import Tuple

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24
except ImportError:
    import fitz  # PyMuPDF < 1.24

logger = logging.getLogger(__name__)

# If a PDF page has fewer than this many characters of native text,
# we treat it as a scanned page and trigger OCR fallback.
OCR_FALLBACK_THRESHOLD = 50
MAX_FILE_SIZE_MB = 100


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract all text from a local PDF with production-level robustness.

    Strategy per page:
      1. Try native PyMuPDF text extraction (fast, lossless).
      2. If the page yields < OCR_FALLBACK_THRESHOLD chars, render it
         as an image and run Tesseract OCR automatically.

    Returns a single string with page-break markers, or a clean error message.
    """
    path = Path(file_path)

    # --- Input validation ---
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if path.suffix.lower() != ".pdf":
        return f"Error: Expected a .pdf file, got '{path.suffix}': {file_path}"
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return f"Error: File too large ({size_mb:.1f} MB). Max allowed: {MAX_FILE_SIZE_MB} MB."

    logger.info(f"Extracting text from PDF: {file_path} ({size_mb:.2f} MB)")

    pages_text = []
    ocr_pages = []

    try:
        with fitz.open(path) as doc:
            total_pages = doc.page_count
            logger.info(f"PDF has {total_pages} page(s).")

            for page_num, page in enumerate(doc, start=1):
                native_text = page.get_text("text").strip()

                if len(native_text) >= OCR_FALLBACK_THRESHOLD:
                    pages_text.append(f"--- Page {page_num} ---\n{native_text}")
                else:
                    # Scanned page: render to image and OCR
                    logger.info(f"Page {page_num} has sparse text ({len(native_text)} chars). Triggering OCR fallback.")
                    ocr_pages.append(page_num)

                    # Render page at 2x resolution for better OCR accuracy
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)

                    # Import here to avoid circular dependency issues
                    from ocr.engine import extract_text_from_pixmap
                    ocr_text = extract_text_from_pixmap(pix)
                    pages_text.append(f"--- Page {page_num} [OCR] ---\n{ocr_text}")

        result = "\n\n".join(pages_text)
        if ocr_pages:
            result += f"\n\n[Note: Pages {ocr_pages} were scanned and processed via OCR.]"

        if not result.strip():
            return "Warning: PDF appears to be empty or entirely unreadable."

        logger.info(f"Extraction complete. Total characters: {len(result)}")
        return result

    except fitz.FileDataError as exc:
        return f"Error: Corrupted or invalid PDF '{file_path}': {exc}"
    except Exception as exc:
        logger.exception(f"Unexpected error parsing PDF: {exc}")
        return f"Error: Unexpected failure reading '{file_path}': {exc}"


def get_pdf_metadata(file_path: str) -> dict:
    """Returns metadata dictionary (title, author, page count, etc.) for a PDF."""
    path = Path(file_path)
    if not path.exists() or path.suffix.lower() != ".pdf":
        return {"error": f"Invalid or missing PDF: {file_path}"}
    try:
        with fitz.open(path) as doc:
            meta = doc.metadata or {}
            meta["page_count"] = doc.page_count
            meta["file_size_mb"] = round(path.stat().st_size / (1024 * 1024), 2)
            return meta
    except Exception as exc:
        return {"error": str(exc)}
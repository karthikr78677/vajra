"""
Production-grade unified document text extraction and image analysis tool.
Wraps PDF parsing, OCR fallback, direct image OCR, and VLM image analysis.
"""

import logging
from pathlib import Path

from ocr.engine import extract_text_from_image
from preprocessing.parser import extract_text_from_pdf, get_pdf_metadata
from vision.analyzer import analyze_image as run_image_analysis

logger = logging.getLogger(__name__)

# All file types supported by this tool
PDF_TYPES = {".pdf"}
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
ALL_SUPPORTED = PDF_TYPES | IMAGE_TYPES


def extract_text(file_path: str, lang: str = "eng") -> str:
    """
    Production-grade unified text extractor callable by the Agent Orchestrator.

    Capabilities:
    - PDF (native text): Fast PyMuPDF extraction.
    - PDF (scanned): Automatic per-page OCR fallback via Tesseract.
    - Images (JPG, PNG, TIFF, BMP): Direct Tesseract OCR with preprocessing.

    Args:
        file_path: Absolute or relative path to the document or image file.
        lang: OCR language code (default: 'eng'). Example: 'eng+hin' for Hindi+English.

    Returns:
        Extracted text as a string, or a descriptive error message.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    logger.info(f"extract_text called: '{file_path}' (type: '{suffix}', lang: '{lang}')")

    # Validate extension
    if suffix not in ALL_SUPPORTED:
        return (
            f"Error: Unsupported file type '{suffix or 'unknown'}'. "
            f"Supported types: PDF, JPG, JPEG, PNG, TIF, TIFF, BMP."
        )

    # Validate existence early for a clear error message
    if not path.exists():
        return f"Error: File does not exist: {file_path}"

    if suffix in PDF_TYPES:
        return extract_text_from_pdf(file_path)

    if suffix in IMAGE_TYPES:
        return extract_text_from_image(file_path, lang=lang)

    return f"Error: Unhandled file type '{suffix}'."  # Should never reach here


def get_document_info(file_path: str) -> str:
    """
    Returns a human-readable summary of document metadata (PDF only).
    Useful for the agent to understand a document before extracting all text.
    """
    path = Path(file_path)
    if path.suffix.lower() != ".pdf":
        return f"Metadata is only available for PDF files. Got: '{path.suffix}'"

    meta = get_pdf_metadata(file_path)
    if "error" in meta:
        return f"Error fetching metadata: {meta['error']}"

    lines = [
        f"Title      : {meta.get('title') or 'N/A'}",
        f"Author     : {meta.get('author') or 'N/A'}",
        f"Pages      : {meta.get('page_count', 'N/A')}",
        f"File size  : {meta.get('file_size_mb', 'N/A')} MB",
        f"Created    : {meta.get('creationDate') or 'N/A'}",
    ]
    return "\n".join(lines)


def analyze_image(file_path: str, question: str = "") -> str:
    """Analyze a photo, drawing, or P&ID schematic using the local vision model."""
    return run_image_analysis(image_path=file_path, prompt=question)

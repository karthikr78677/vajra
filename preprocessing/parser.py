"""PDF text extraction for local documents."""

from pathlib import Path

import fitz


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a local PDF, returning a clean error on failure."""
    path = Path(file_path)
    if not path.is_file():
        return f"Error: PDF file not found: {file_path}"
    if path.suffix.lower() != ".pdf":
        return f"Error: Expected a PDF file: {file_path}"

    try:
        with fitz.open(path) as document:
            return "\n".join(page.get_text() for page in document)
    except (OSError, RuntimeError, ValueError) as exc:
        return f"Error: Could not read PDF '{file_path}': {exc}"
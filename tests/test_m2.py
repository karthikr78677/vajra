from pathlib import Path

import fitz

from tools.vision_tool import extract_text


def test_extract_text_from_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "report.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Inspection complete")
    document.save(pdf_path)
    document.close()

    assert "Inspection complete" in extract_text(str(pdf_path))


def test_extract_text_rejects_missing_and_unsupported_files(tmp_path: Path) -> None:
    assert extract_text(str(tmp_path / "missing.pdf")).startswith("Error: PDF file not found")
    assert "Unsupported file type" in extract_text(str(tmp_path / "notes.txt"))
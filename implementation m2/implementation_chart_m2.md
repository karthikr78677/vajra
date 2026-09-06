# Vajra M2 Implementation Chart

## Module Scope

**Module:** M2 - Preprocessing and OCR  
**Goal:** Extract text locally from PDF, JPG, JPEG, and PNG files for use by the Agent Orchestrator.  
**Privacy requirement:** All processing remains local; no external service is contacted.

## Implementation Chart

| Stage | Component | File | Responsibility | Status |
|---|---|---|---|---|
| 1 | PDF parser | `preprocessing/parser.py` | Open local PDFs with PyMuPDF (`fitz`) and extract text from every page. | Complete |
| 2 | OCR engine | `ocr/engine.py` | Open local JPG/JPEG/PNG files with Pillow and extract text with `pytesseract`. | Complete |
| 3 | Environment configuration | `.env` | Provide the local Tesseract executable path through `TESSERACT_CMD`. | Supported |
| 4 | Unified tool | `tools/vision_tool.py` | Dispatch extraction by file extension and return clean errors for unsupported or missing files. | Complete |
| 5 | Agent integration | `agents/orchestrator.py` | Expose the `extract_text` tool to the Plan -> Act -> Observe -> Retry loop. | Complete |
| 6 | Dependencies | `requirements.txt` | Declare PyMuPDF, pytesseract, Pillow, and python-dotenv. | Complete |
| 7 | Verification | `tests/test_m2.py` | Verify PDF extraction and missing/unsupported-file handling. | Complete |

## Runtime Flow

```text
Local file path
      |
      v
vision_tool.extract_text()
      |
      +-- .pdf  ------> preprocessing.parser.extract_text_from_pdf()
      |
      +-- .jpg/.jpeg/.png -> ocr.engine.extract_text_from_image()
      |
      v
Extracted text or controlled error string
      |
      v
Agent Orchestrator observation
```

## Error-Handling Rules

- Missing files return an `Error:` string rather than raising an unhandled exception.
- Non-PDF files passed to the PDF parser return a controlled error.
- Non-JPG/PNG files passed to the OCR engine return a controlled error.
- Unsupported extensions are rejected by the unified tool.
- Invalid or unreadable files return a controlled error containing the file path and failure reason.
- If `TESSERACT_CMD` is configured, it is assigned to `pytesseract` at module load time.

## Dependencies

```text
pymupdf>=1.23.4
pytesseract>=0.3.10
Pillow>=10.0.0
python-dotenv>=1.0.0
```

## Local Configuration

Create a local `.env` file at the repository root:

```env
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

The `.env` file is ignored by Git and must not contain committed secrets or machine-specific configuration.

## Verification Checklist

- [x] Pull latest `origin/main` before implementation.
- [x] Install dependencies with `uv pip install -r requirements.txt`.
- [x] Compile the M2 modules successfully.
- [x] Extract text from a generated PDF successfully.
- [x] Return a clean error for a missing PDF.
- [x] Return a clean error for an unsupported file type.
- [ ] Run the OCR test with Tesseract installed and `TESSERACT_CMD` configured.
- [ ] Run the complete project test suite after `pytest` is installed.

## Ownership and Boundaries

M2-owned implementation files:

- `preprocessing/`
- `ocr/`
- `tests/test_m2.py`

Integration files touched for tool availability:

- `tools/vision_tool.py`
- `agents/orchestrator.py`
- `requirements.txt`

Shared configuration and generated local files must remain uncommitted.

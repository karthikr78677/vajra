# Vajra — Implementation Plan

This plan details the end-to-end implementation of Vajra, a self-hosted, air-gapped AI workbench designed for industrial and confidential document work (SIH PS117). The solution leverages small open-weight models routed dynamically through Ollama to respect a strict 4GB VRAM constraint.

The implementation will follow the 20-hour (2-day) schedule, covering:
1. **Scenario A:** Scanned report → OCR → Agent drafts approval note (.docx)
2. **Scenario B:** Coding prompt → Code generated → Sandbox execution → Verified
3. **Scenario C:** Image/drawing → Vision model → Extracted findings

## User Review Required

> [!WARNING]
> We must respect the **4GB VRAM limit**. We will implement a `Model Router` that unloads and loads models via Ollama sequentially. Only one model can be active at a time.
> **All models must be pulled via Ollama before proceeding with testing.**
> We will need `Qwen2.5-3B-Instruct`, `Qwen2.5-Coder-1.5B-Instruct`, and `moondream2` in Ollama, plus the sentence transformers embedding model.

## Open Questions

> [!IMPORTANT]
> 1. Do you want to build this repository sequentially as a single developer, or should we focus on a specific module (e.g., just the M1 Backend and M4 Agents) first?
> 2. Is Ollama currently installed on your Windows machine, and have you already pulled any of the required models?
> 3. Do you have Tesseract OCR installed on this machine? It will be required for the M2 (Preprocessing & OCR) tasks.

## Proposed Changes

We will create the directory structure and files as specified in `folder_structure.md`. Here is the module-by-module breakdown.

### [Module 1] Backend, Router, Network Monitor
#### [NEW] `backend/main.py`
FastAPI app entrypoint handling routes for upload, processing, and agent tasks.
#### [NEW] `backend/router.py`
Model router that switches Ollama models on demand.
#### [NEW] `backend/task_analysis.py`
Classifies incoming requests into reasoning, coding, or vision intents.
#### [NEW] `backend/schemas.py`
Pydantic JSON contracts (shared models) between stages.
#### [NEW] `models/router_config.yaml`
Config-driven registry tracking model names and sizes.
#### [NEW] `network_monitor/monitor.py`
psutil-based live traffic monitor to prove air-gap/sovereignty.

### [Module 2] Preprocessing & OCR
#### [NEW] `preprocessing/pdf_parser.py`
PyMuPDF (fitz) integration for parsing PDF text and images.
#### [NEW] `ocr/ocr_engine.py`
pytesseract wrapper with deskew/thresholding preprocessing.

### [Module 3] Vision
#### [NEW] `vision/vision_engine.py`
moondream2 wrapper for extracting insights from engineering drawings.

### [Module 4] Agents & Tools
#### [NEW] `agents/orchestrator.py`
Custom state machine (Plan → Act → Observe → Retry) for agent flow.
#### [NEW] `tools/file_tool.py`
Local file read/write operations.
#### [NEW] `tools/calculator_tool.py`
Safe mathematical operations.
#### [NEW] `tools/sandbox_exec.py`
Sandboxed python code execution using `subprocess` with timeouts.

### [Module 5] Knowledge Base
#### [NEW] `knowledge_base/ingest.py`
Loads SOPs into ChromaDB using `all-MiniLM-L6-v2` embeddings.
#### [NEW] `knowledge_base/retrieve.py`
Semantic search functionality over local vector DB.

### [Module 6] Frontend & Document Generation
#### [NEW] `frontend/app.py`
Streamlit UI combining upload, task flow, reasoning trace, and downloads.
#### [NEW] `document_generation/docx_gen.py`
Generates `.docx` approval notes.
#### [NEW] `document_generation/xlsx_gen.py`
Generates Excel reports.
#### [NEW] `document_generation/pptx_gen.py`
Generates PowerPoint summaries.

---

## Verification Plan

### Automated Tests
- Build out unit tests in `tests/test_preprocessing.py`, `tests/test_ocr.py`, `tests/test_agent.py`, `tests/test_knowledge_base.py`, etc.
- Run `pytest` locally to ensure isolated components function properly.

### Manual Verification
1. **Scenario A Test:** Upload a sample image/PDF to Streamlit → Ensure OCR extracts text → Ensure reasoning model uses retrieved SOP to generate a `docx` file.
2. **Scenario B Test:** Input a coding query → Ensure the coding model generates a script → Ensure the sandbox executes it without crashing the FastAPI server.
3. **Scenario C Test:** Upload a diagram → Ensure the vision model outputs a correct description.
4. **Air-gapped Proof:** Start `network_monitor/monitor.py` and run a full pipeline test to verify zero bytes of external outbound traffic (excluding localhost Ollama).

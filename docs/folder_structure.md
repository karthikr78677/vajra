# Vajra — Project Folder Structure

This is the authoritative folder layout for the Vajra project (SIH PS117 — Sovereign
On-Premise Agentic AI Workbench). Every module has one owner. Agents and team members
must only create/modify files inside their assigned folder(s) unless explicitly told
otherwise. Shared files (marked below) require review from M1 before merging.

```
vajra/
│
├── frontend/                 # OWNER: M6
│   └── app.py                 # Streamlit app — upload widget, task flow, download button
│
├── backend/                  # OWNER: M1
│   ├── main.py                 # [SHARED - M1 review required] FastAPI app entrypoint
│   ├── router.py                # Model Router — picks reasoning/coding/vision model per task
│   ├── task_analysis.py         # Classifies incoming request into a task type
│   └── schemas.py               # [SHARED - M1 review required] JSON contracts between stages
│
├── models/                   # OWNER: M1
│   └── router_config.yaml       # [SHARED - M1 review required] Config-driven model registry
│
├── preprocessing/            # OWNER: M2
│   └── pdf_parser.py            # PyMuPDF-based PDF text/image extraction
│
├── ocr/                      # OWNER: M2
│   └── ocr_engine.py            # Tesseract/PaddleOCR wrapper, deskew/threshold preprocessing
│
├── vision/                   # OWNER: M3
│   └── vision_engine.py         # moondream2 wrapper, image/drawing prompt templates
│
├── agents/                   # OWNER: M4
│   └── orchestrator.py          # Plan -> Act -> Observe -> Retry state machine
│
├── tools/                    # OWNER: M4
│   ├── file_tool.py              # File read/write tool
│   ├── calculator_tool.py        # Safe calculator tool
│   └── sandbox_exec.py           # Sandboxed code execution (subprocess + timeout)
│
├── knowledge_base/           # OWNER: M5
│   ├── ingest.py                 # Loads SOPs/manuals into ChromaDB with embeddings
│   └── retrieve.py               # search_knowledge_base(query) — embedding-based vector retrieval
│
├── document_generation/      # OWNER: M6
│   ├── docx_gen.py               # Word approval-note generator (python-docx) — MUST HAVE
│   ├── xlsx_gen.py               # Excel generator (openpyxl) — SHOULD HAVE
│   └── pptx_gen.py               # PowerPoint generator (python-pptx) — SHOULD HAVE
│
├── network_monitor/           # OWNER: M1
│   └── monitor.py                # psutil-based live traffic monitor (sovereignty proof)
│
├── tests/                     # OWNER: all — each member adds tests for their own module
│   ├── test_preprocessing.py
│   ├── test_ocr.py
│   ├── test_agent.py
│   ├── test_knowledge_base.py
│   └── test_document_generation.py
│
├── data/                      # OWNER: all — shared sample/demo files only
│   ├── sample_scanned_reports/   # Synthetic/dummy scanned inspection reports for testing
│   ├── sample_sops/              # Synthetic/dummy SOP and manual text files for the KB
│   └── sample_images/            # Synthetic/dummy images for OCR/vision testing
│
├── configs/                   # OWNER: M1 — environment configs, .env.example
│
├── scripts/                   # OWNER: all — setup/run helper scripts
│   └── setup_env.sh              # One-shot environment setup script
│
├── docs/                       # Reference documents for the team AND for AI coding agents
│   ├── problem_statement.txt      # Original SIH PS117 problem statement
│   ├── SIH_PS117_Plan.md          # Full architecture, model choices, schedule, risks
│   ├── architecture_diagram.png   # Pipeline diagram
│   └── folder_structure.md        # This file
│
├── requirements.txt            # [SHARED - M1 review required] Python dependencies
├── README.md                   # Setup instructions, how to run, how to add a new model
└── .env                        # Local secrets/config — never committed (in .gitignore)
```

## Rules for AI coding agents (Antigravity, Claude Code, etc.) working in this repo

1. **Only touch your assigned folder(s).** If your task requires changing a file outside
   your folder, stop and flag it instead of making the change yourself.
2. **Never modify files marked `[SHARED - M1 review required]`** without explicit
   instruction in your prompt for that session. These are the integration contracts
   every other module depends on.
3. **Never commit real confidential-looking data.** Everything in `data/` must be
   synthetic/dummy — this repo is public.
4. **Don't restructure this folder layout.** If you think a different structure would be
   better, say so in your response — do not silently reorganize files.
5. **Match the module boundaries above exactly** when creating new files — e.g., OCR
   code goes in `ocr/`, never inside `preprocessing/`, even if it feels related.

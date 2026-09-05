# Vajra — PS 117 Implementation Plan (CURRENT: 2-Day / 20-Hour, Full Scope Restored)

> **This is the authoritative, current plan.** All 3 demo scenarios, real RAG, and full
> document generation (Word + Excel + PPT) are back in scope, compressed into 2 days x
> significantly cuts implementation time on boilerplate and wiring. AI coding agents
> should treat this document as the single source of truth.

---

## 0. Reality Check — What Compresses With Antigravity, and What Doesn't

| Compresses well (agent speed helps) | Does NOT compress (fixed wall-clock time) |
|---|---|
| FastAPI routes, docx/xlsx/pptx generators, tool functions, Streamlit UI, boilerplate wiring | **Downloading models** — pulling Qwen2.5-3B, Qwen2.5-Coder-1.5B, moondream2, and the embedding model via Ollama takes real minutes regardless of coding speed |
| Agent state machine, router logic, embeddings/RAG wiring, first-draft OCR/vision wrappers | **Model inference time during testing** — every test prompt through a local model is real seconds/minutes |
| Debugging syntax/logic errors | **OCR/vision accuracy tuning** — empirical, requires real sample iteration, not just faster code |
| | **Live dry-run rehearsals** — literally clock-time, cannot be parallelized away |

**Action taken to save real time:** all 4 models (reasoning, coding, vision, embeddings)
are pulled via Ollama **before Day 1 officially starts**, in the background, so Day 1
Hour 1 doesn't lose time to downloads.

**Core VRAM rule (unchanged):** only one small quantized LLM sits in VRAM at a time. The
Model Router loads/unloads via Ollama on demand — this is how "multiple models,
auto-selected per task" works on 4GB VRAM. OCR and embeddings run on CPU always.

**Honest trade-off accepted by compressing to 20 hours with full scope:** there is
effectively **zero dedicated hardening day**. Only one full dry-run fits before demo,
versus two-plus in the original 52-hour plan. Mitigate by caching a "known-good" run
(screenshots + saved outputs) the moment each scenario first works, not at the end.

---

## 1. Team & Roles (6 members, full scope)

| Member | Role | Owns (folders) |
|---|---|---|
| **M1** | Backend, Router, Agent Orchestrator, Network Monitor | `backend/`, `models/`, `network_monitor/` |
| **M2** | Preprocessing & OCR | `preprocessing/`, `ocr/` |
| **M3** | Vision & Multimodal | `vision/` |
| **M4** | Agent loop + Tools | `agents/`, `tools/` |
| **M5** | Knowledge Base / RAG (embeddings + vector DB) | `knowledge_base/` |
| **M6** | Document Generation (Word/Excel/PPT) & UI | `frontend/`, `document_generation/` |

No floater role in this version — all 6 members have a dedicated module, since the
restored scope needs every workstream staffed.

---

## 2. Model Selection (4GB VRAM budget, unchanged principle)

| Task | Model | Size | Quantization | Notes |
|---|---|---|---|---|
| Reasoning / drafting | Qwen2.5-3B-Instruct | 3B | Q4_K_M GGUF | ~2.0-2.3GB VRAM. Fallback: Qwen2.5-1.5B-Instruct if too slow |
| Coding | Qwen2.5-Coder-1.5B-Instruct | 1.5B | Q4_K_M GGUF | ~1.0GB VRAM |
| Vision / multimodal | moondream2 | 1.6B | native int4/fp16-lite | ~1.5-2GB VRAM. Purpose-built lightweight VLM |
| OCR | Tesseract OCR | N/A | CPU only | Zero GPU cost |
| Embeddings (RAG) | all-MiniLM-L6-v2 | 22M | CPU (fp32) | Fast, no GPU needed |
| Vector DB | ChromaDB (local, persistent) | N/A | CPU | Simple local file-based store |

**Pull all 4 Ollama models + the embedding model before Day 1 starts** — this is the
single biggest real-time saver available.

---

## 3. Technology Stack (full scope)

| Layer | Choice |
|---|---|
| Inference runtime | Ollama (on-demand model swap) |
| Backend | FastAPI |
| UI | Streamlit |
| PDF parsing | PyMuPDF (fitz) |
| OCR | Tesseract via pytesseract |
| Vision | Ollama (moondream2) |
| Vector DB | ChromaDB (local, persistent) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Document generation | python-docx, openpyxl, python-pptx (all 3 restored) |
| Agent orchestration | Custom ~150-line Python state machine (Plan -> Act -> Observe -> Retry) — NOT LangGraph |
| Code sandbox | Restricted `subprocess` with timeout |
| Network-isolation proof | `psutil`-based traffic monitor + physically disabled Wi-Fi/Ethernet |
| Version control | Git + GitHub — branches: `main`, `dev`, `m1`-`m6` |
| Development environment | Google Antigravity — one workspace per branch; shared files (`schemas.py`, `router_config.yaml`, `main.py`) stay human/M1-reviewed |
| Python version | 3.11.x (pinned via `.python-version`) |

---

## 4. Pipeline (must work end-to-end by end of Day 1, all 3 scenarios by end of Day 2)

```
User Input (file/text/image)
   -> Local Preprocessing (M2: PDF/image parse, OCR)
   -> Task Analysis (M1: classify intent - reasoning / coding / vision)
   -> Model Router (M1: pick + load correct Ollama model)
   -> Local Model (Reasoning / Coding / Vision - one at a time)
   -> Agent Orchestrator (M4: Plan -> Act -> Observe -> Retry)
   -> Local Knowledge/Tools (M5: RAG retrieval, M4: file/calculator/sandbox tools)
   -> Final Deliverable (M6: Word/Excel/PPT, or verified code + logs)
```

---

## 5. Feature Classification (full scope, 20-hour build)

### MUST HAVE
- Local model serving via Ollama, 3 models (reasoning/coding/vision), auto-selected by task
- Config-driven model registry (`router_config.yaml`)
- PDF/image preprocessing + OCR
- Task Analysis classifying reasoning vs. coding vs. vision
- Model Router wired to Task Analysis
- Scenario A: scanned report -> OCR -> agent drafts findings -> approval note (.docx)
- Scenario B: coding prompt -> code generated -> sandbox-executed -> verified
- Scenario C: image/drawing -> vision model -> extracted findings/summary
- Real RAG: embeddings + ChromaDB over a curated SOP set
- Single unified Streamlit UI tying all 3 scenarios together
- Live proof of zero external network calls during a full run

### SHOULD HAVE (only if ahead of schedule)
- Excel and PPT generation in addition to Word
- Agent retry/error-recovery logic beyond a single retry
- Visible "agent reasoning trace" in the UI

### OUT OF SCOPE (still, even at full restored scope)
- Any 7B+ model — too slow for a live demo on 4GB VRAM
- Fine-tuning/training any model
- Docker-based sandbox — subprocess+timeout is sufficient
- Reranking layer on RAG retrieval
- Handwriting OCR beyond a single best-effort sample

---

## 6. Day-by-Day Schedule (2 days x 10 hours, full scope)

### Before Day 1 (not counted in the 20 hours)
All 6 members pull Qwen2.5-3B-Instruct, Qwen2.5-Coder-1.5B-Instruct, moondream2, and the
embedding model via Ollama, in parallel, ahead of kickoff.

### DAY 1 (10 hours) — Foundation + Scenario A + Scenario C wired

| Hour | M1 | M2 | M3 | M4 | M5 | M6 |
|---|---|---|---|---|---|---|
| 1 | **All members:** freeze architecture + JSON schemas | | | | | |
| 2-3 | FastAPI skeleton; verify all 3 models respond via Ollama REST | PyMuPDF + Tesseract setup; `extract_text()` | moondream2 wrapper; `describe_image()` | Tool-calling JSON contract; file + calculator tools | ChromaDB setup; embeddings on 5 sample SOPs | Streamlit skeleton; docx/xlsx/pptx generator stubs |
| 4-5 | Model Router (task classifier: reasoning/coding/vision), wire to FastAPI | OCR wired into `/upload`; test on real samples | Vision wired into `/upload`; test on real images | Sandboxed code executor (subprocess + timeout) | `/rag-query` endpoint; chunking strategy | Approval-note docx template with real formatting |
| 6-7 | Full agent orchestrator (150-line state machine), wired to router | OCR error handling; multi-page scans | Vision confidence fallback; test on P&ID-style images | Wire file/calculator/sandbox + KB search into agent's tool contract | Metadata-enriched chunking; retrieval quality pass | Coding-output packaging (code+log); xlsx/pptx generators with real content |
| 8-9 | **M1+M2+M4+M6 jointly:** wire Scenario A (doc -> approval note) | | **M1+M3+M4 jointly:** wire Scenario C (image -> findings) in parallel thread | (split across both scenario threads) | Ensure agent pulls a KB line into Scenario A's note | (split across both scenario threads) |
| 10 | **All members:** integration checkpoint - run Scenario A and Scenario C live, fix breakage, push to `dev` | | | | | |

**End of Day 1 checkpoint:** Scenarios A and C work end-to-end at least once (rough is fine). Scenario B's individual pieces (coding model, sandbox executor, tool contract) are built and unit-tested standalone, ready to wire on Day 2 morning.

### DAY 2 (10 hours) — Scenario B wiring + full integration + hardening

| Hour | M1 | M2 | M3 | M4 | M5 | M6 |
|---|---|---|---|---|---|---|
| 1-2 | Wire `/agent-task` + unified `/process` endpoint | Bug-fix OCR from Day 1 | Bug-fix vision from Day 1 | **Wire Scenario B** (coding -> sandbox -> verified) | Bug-fix retrieval edge cases | Full Streamlit flow handling all 3 scenarios |
| 3-4 | Build network-isolation monitor (`psutil` traffic counters) | Stress-test OCR: 5 more samples | Stress-test vision: 5 more samples | Debug Scenario B with 3 coding prompts | Expand KB to 8-10 realistic docs | Bug-fix docx/xlsx/pptx formatting on real content |
| 5-6 | **All members:** full pipeline test - Scenario A via UI only | | | | | |
| 7 | **All members:** full pipeline test - Scenario B via UI only | | | | | |
| 8 | **All members:** full pipeline test - Scenario C via UI only | | | | | |
| 9 | Model pre-warm, swap-latency polish | OCR caching for demo files | Vision caching for demo files | Retry cap tuning, reasoning trace in UI | Pre-load KB at startup | UI polish, reasoning trace display |
| 10 | **All members:** dry-run #1, fix critical issues, cache backup outputs/screenshots, quick README, assign presentation roles | | | | | |

**End of Day 2 checkpoint:** All 3 scenarios demo-ready, network-isolation proof working, backup materials cached, team rehearsed at least once.

---

## 7. Git Workflow

- **Branches:** `main` (protected, demo-ready only), `dev` (shared integration branch), `m1`-`m6` (one personal branch per member)
- **Daily routine (every member, every session):**
  ```
  git checkout dev && git pull origin dev
  git checkout <my-branch> && git merge dev
  ... work, commit in small chunks ...
  git push origin <my-branch>
  ```
- **Merge to `dev`:** at the scheduled Integration Checkpoints only (Day 1 Hour 10; Day 2 Hours 5-6, 7, 8, 10)
- **Merge authority:** self-merge if only your own folder is touched; M1 reviews anything touching `schemas.py`, `router_config.yaml`, or `main.py`
- **`dev` -> `main`:** promoted by M1 after Day 2's final checkpoint
- See `Vajra_Team_Collaboration_Guide.pdf` for the full beginner walkthrough

---

## 8. Folder Structure

See `folder_structure.md` (companion file). At full restored scope, `vision/`,
`xlsx_gen.py`, and `pptx_gen.py` are all **active, in-scope modules** — not placeholders.

---

## 9. Risks (full scope, 20 hours)

| Risk | Prevention | Backup |
|---|---|---|
| Zero hardening day — one bad bug eats the schedule | Cache a "known-good" run (screenshots + saved outputs) the moment each scenario first works, not at the end | Pre-recorded run + cached output files as fallback per scenario |
| 3 scenarios means 3x the live-demo failure surface | Test each scenario's exact demo input specifically by its "full pipeline test" hour, not generic samples | Curate 1 known-good input per scenario, used only for the live demo |
| Model download time eats into Day 1 | Pull all 4 models before Day 1 officially starts | If a model isn't ready, fall back to the smaller alternative (1.5B reasoning, skip vision confidence tuning) |
| Small quantized models produce malformed JSON tool calls | Single retry with error feedback built into the agent loop | Hardcode the expected next tool call for the known demo input only, as last resort |
| Only one dry-run fits before the demo | Treat Day 2 Hour 10 as non-negotiable — do not let bug-fixing eat into it | If Hour 9 testing reveals a blocker, cut a SHOULD HAVE feature immediately rather than delaying the dry-run |
| Judges probe "why only 1.5-3B models" | Have the VRAM-constraint answer ready: architecture is model-size-agnostic, same router pattern scales to 120B-class models on production GPU hardware | N/A |

---

## 10. Demo Strategy (3 scenarios, 7-10 minutes)

1. Show Wi-Fi/Ethernet disabled + live network monitor (flat traffic)
2. **Scenario A:** upload scanned inspection report -> OCR -> task classified -> agent drafts approval note grounded in a KB clause -> downloadable `.docx`
3. **Scenario B:** type a coding request -> coding model generates code -> sandbox executes it live -> verified output + logs shown
4. **Scenario C:** upload a photo/scan of an engineering drawing or label -> vision model extracts and summarizes key details
5. Point back to network monitor - zero external calls throughout
6. Show `router_config.yaml`, add a fake new model entry live to prove "no redesign needed"
7. Close: recap architecture, mention production-hardware scaling (bigger models, more GPUs) as future work

**Backup plan:** pre-recorded screen capture of a successful dry-run per scenario, plus pre-generated output files kept on hand to open directly if live inference is slow.

---

## 11. Working in Google Antigravity

- One Antigravity workspace per branch (`m1`-`m6`)
- Feed each agent this document + `folder_structure.md` + the original problem statement before any task
- Agents work only within their owned folders; shared files stay human/M1-reviewed
- Use the Manager Surface to run M2/M3/M5/M6's independent module-building in parallel during Hours 2-7 of Day 1 — this is where agent-assisted speed matters most
- Antigravity's coding agents use cloud models during development only — separate from the deployed air-gapped product, does not affect the sovereignty claim

---

## 12. Definition of Done (full scope, 20-hour version)

1. All 3 scenarios run successfully via the UI, at least once each, by end of Day 2 Hour 9
2. Network monitor shows zero outbound traffic during a full run, Wi-Fi/Ethernet physically disabled
3. One generated Word document, one executed+verified code sample, and one vision-extracted summary saved as backup demo artifacts
4. Short README documents setup, model list, and how to add a new model to the router
5. Every team member can demo their module in under 60 seconds if asked

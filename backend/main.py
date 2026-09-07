from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import logging
import time
import os
import json
import uuid
import aiofiles
from pathlib import Path
from typing import List
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.schemas import (
    UserRequest, TaskAnalysisResult, TaskResponse,
    TaskType, PermissionApproveRequest, IngestRequest
)
from backend.task_analysis import analyze_task_async
from backend.router import ModelRouter
from agents.orchestrator import AgentOrchestrator
from agents.permission_manager import permission_manager
from backend.document_registry import (
    get_document, list_documents, list_all_documents,
    mark_indexed, register_upload, delete_document
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vajra - Air-gapped AI Workbench (Advanced M1)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = ModelRouter()

# Upload directory — lives inside VAJRA_WORKSPACE
WORKSPACE = Path(os.getenv("VAJRA_WORKSPACE", os.path.dirname(os.path.dirname(__file__))))
UPLOAD_DIR = WORKSPACE / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Supported extensions for workspace folder ingestion
INGESTABLE_EXTS = {".txt", ".md", ".pdf", ".docx", ".csv", ".json", ".xlsx"}


def extract_document_text(path: Path) -> str:
    """Extract text from any supported upload format into a plain string."""
    ext = path.suffix.lower()

    # ── Plain text formats ────────────────────────────────────────────────────
    if ext in {".txt", ".md", ".json"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    # ── CSV: use pandas for correct tabular reading ───────────────────────────
    if ext == ".csv":
        try:
            import pandas as pd
            df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
            return df.to_string(index=False)
        except Exception:
            return path.read_text(encoding="utf-8", errors="ignore")

    # ── Excel: iterate rows with column headers ───────────────────────────────
    if ext in {".xlsx", ".xls"}:
        from openpyxl import load_workbook
        book = load_workbook(str(path), read_only=True, data_only=True)
        lines = []
        for sheet in book.worksheets:
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                continue
            # First row as headers
            headers = [str(c) if c is not None else "" for c in rows[0]]
            lines.append("  ".join(headers))
            for row in rows[1:]:
                values = [str(c) if c is not None else "" for c in row]
                # Skip fully empty rows
                if any(v.strip() for v in values):
                    lines.append("  ".join(values))
        return "\n".join(lines)

    # ── PDF / images: OCR via vision tool ────────────────────────────────────
    if ext in {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"}:
        from tools.vision_tool import extract_text
        return extract_text(str(path))

    # ── Word documents ────────────────────────────────────────────────────────
    if ext == ".docx":
        from docx import Document
        return "\n".join(p.text for p in Document(str(path)).paragraphs)

    raise ValueError(f"Unsupported file type: {ext or 'unknown'}")


def index_registered_document(
    record: dict, domain: str | None = None, shared: bool = False
) -> int:
    """Index a registered upload with immutable document-scoped metadata."""
    from knowledge_base.ingest import ingest_document

    source_path = Path(record["path"])
    if not source_path.exists():
        raise FileNotFoundError(f"Uploaded file is no longer available: {record['name']}")
    extracted_path = UPLOAD_DIR / ".extracted" / f"{record['document_id']}.txt"
    extracted_path.parent.mkdir(parents=True, exist_ok=True)
    extracted_path.write_text(extract_document_text(source_path), encoding="utf-8")
    count = ingest_document(
        str(extracted_path), document_id=record["document_id"], source_name=record["name"], shared=shared
    )
    mark_indexed(record["document_id"], domain, shared)
    return count

@app.on_event("shutdown")
async def shutdown_event():
    await router.close()

# ─────────────────────────────────────────────────────────────────────────────
# FILE UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Accept multipart file upload(s) from the frontend.
    Saves each file to VAJRA_WORKSPACE/uploads/ and returns their absolute paths.
    """
    saved_paths = []
    documents = []
    errors = []
    for upload in files:
        try:
            original_name = Path(upload.filename or "upload").name
            dest = UPLOAD_DIR / f"{uuid.uuid4().hex}_{original_name}"
            content = await upload.read()
            async with aiofiles.open(dest, "wb") as f:
                await f.write(content)
            saved_paths.append(str(dest))
            record = register_upload(original_name, dest, len(content))
            documents.append(record)
            logger.info(f"Uploaded: {dest}")

            # ── Auto-index immediately so the doc appears in the DB list ──────
            import asyncio as _asyncio
            def _sync_index():
                try:
                    index_registered_document(record, domain="Uploads", shared=True)
                    logger.info(f"Auto-indexed: {original_name} ({record['document_id']}")
                except Exception as idx_err:
                    logger.error(f"Auto-index failed for {original_name}: {idx_err}")
            _asyncio.get_event_loop().run_in_executor(None, _sync_index)

        except Exception as e:
            errors.append({"file": upload.filename, "error": str(e)})
            logger.error(f"Upload failed for {upload.filename}: {e}")

    return {"paths": saved_paths, "documents": documents, "errors": errors}


@app.get("/documents")
async def list_indexed_documents():
    """List ALL uploaded documents for the database UI (newest first).
    Returns every upload regardless of indexed/shared status so files
    appear immediately in the UI after upload."""
    docs = list_all_documents()
    return {
        "documents": [
            {
                **doc,
                "type": Path(doc["name"]).suffix.lstrip(".").lower() or "file",
                "size_human": _fmt_size(doc.get("size") or 0),
            }
            for doc in docs
        ]
    }


def _fmt_size(n: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


@app.delete("/documents/{document_id}")
async def delete_document_endpoint(document_id: str):
    """Remove a document from the registry (does not delete the file on disk)."""
    success = delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return {"status": "deleted", "document_id": document_id}

# ─────────────────────────────────────────────────────────────────────────────
# CHROMADB INGEST
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/ingest")
async def ingest_documents(request: IngestRequest):
    """
    Index uploaded files and/or a local workspace folder into ChromaDB.
    Returns the total number of chunks indexed.
    """
    # New callers use immutable document IDs.  Keep the legacy path contract
    # working while translating registered paths back to those identities.
    if request.document_ids:
        total, indexed, errors = 0, [], []
        for document_id in dict.fromkeys(request.document_ids):
            record = get_document(document_id)
            if record is None:
                errors.append({"file": document_id, "error": "Unknown document ID"})
                continue
            try:
                chunks_added = index_registered_document(record, request.domain, shared=True)
                total += chunks_added
                indexed.append({"file": record["name"], "document_id": document_id, "chunks": chunks_added})
            except Exception as exc:
                logger.error("Ingest failed for %s: %s", record["name"], exc)
                errors.append({"file": record["name"], "error": str(exc)})
        return {"status": "success", "indexed_chunks": total, "files": indexed, "errors": errors}

    from knowledge_base.ingest import ingest_document, model, collection

    all_paths: list[str] = list(request.file_paths)

    # Scan workspace folder for supported files
    if request.workspace_path:
        ws = Path(request.workspace_path)
        if not ws.exists():
            raise HTTPException(status_code=400, detail=f"Workspace path does not exist: {request.workspace_path}")
        for ext in INGESTABLE_EXTS:
            all_paths.extend(str(p) for p in ws.rglob(f"*{ext}"))

    if not all_paths:
        return {"status": "no_files", "indexed_chunks": 0, "files": []}

    total = 0
    indexed = []
    errors = []

    for path_str in all_paths:
        path = Path(path_str)
        if not path.exists():
            errors.append({"file": path_str, "error": "File not found"})
            continue
        try:
            ext = path.suffix.lower()
            # Extract text based on type
            if ext == ".pdf":
                from tools.vision_tool import extract_text
                text = extract_text(path_str)
            elif ext in {".jpg", ".jpeg", ".png", ".tiff", ".bmp"}:
                from tools.vision_tool import extract_text
                text = extract_text(path_str)
            else:
                # Plain text / CSV / MD / JSON — read directly
                text = path.read_text(encoding="utf-8", errors="ignore")

            # Use the existing ingest_document function (it handles chunking + embedding)
            # We need to write content to a temp txt if original format is not txt
            if ext != ".txt":
                tmp_path = UPLOAD_DIR / (path.stem + "_extracted.txt")
                tmp_path.write_text(text, encoding="utf-8")
                chunks_added = ingest_document(str(tmp_path))
            else:
                chunks_added = ingest_document(path_str)

            total += chunks_added
            indexed.append({"file": path.name, "chunks": chunks_added})
            logger.info(f"Ingested {path.name}: {chunks_added} chunks")
        except Exception as e:
            errors.append({"file": path_str, "error": str(e)})
            logger.error(f"Ingest failed for {path_str}: {e}")

    return {
        "status": "success",
        "indexed_chunks": total,
        "files": indexed,
        "errors": errors,
    }

# ─────────────────────────────────────────────────────────────────────────────
# PERMISSION APPROVAL ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/permissions")
async def list_pending_permissions():
    """Returns all pending permission requests waiting for user approval."""
    return {"pending": permission_manager.list_pending()}

@app.post("/approve/{task_id}")
async def approve_permission(task_id: str):
    """Approves a pending permission request and resumes the paused agent."""
    pending = permission_manager.get_pending(task_id)
    if not pending:
        raise HTTPException(status_code=404, detail=f"No pending permission for task_id: {task_id}")
    permission_manager.resolve(task_id, approved=True)
    return {"status": "approved", "task_id": task_id, "action": pending.action}

@app.post("/deny/{task_id}")
async def deny_permission(task_id: str):
    """Denies a pending permission request and cancels the paused agent action."""
    pending = permission_manager.get_pending(task_id)
    if not pending:
        raise HTTPException(status_code=404, detail=f"No pending permission for task_id: {task_id}")
    permission_manager.resolve(task_id, approved=False)
    return {"status": "denied", "task_id": task_id, "action": pending.action}

@app.get("/permissions/pending")
async def get_pending_permissions():
    """Returns a list of actions currently waiting for user approval."""
    try:
        pending = permission_manager.list_pending()
        return {"status": "success", "pending": pending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/permissions/approve")
async def approve_permission_body(request: PermissionApproveRequest):
    """Resolves a pending permission request (approved=True or False)."""
    try:
        success = permission_manager.resolve(request.task_id, request.approved)
        if success:
            return {"status": "success", "message": f"Task {request.task_id} resolved."}
        else:
            raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found or already resolved.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# TASK ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/analyze", response_model=TaskAnalysisResult)
async def api_analyze_task(request: UserRequest):
    """Endpoint to classify a user request using hybrid heuristics + LLM fallback."""
    try:
        return await analyze_task_async(request, router)
    except Exception as e:
        logger.error(f"Error in task analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# BLOCKING PROCESS (non-streaming fallback)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/process", response_model=TaskResponse)
async def api_process_task(request: UserRequest):
    """
    Blocking endpoint: analyzes the task and runs the Agent Orchestrator.
    Accepts conversation history for multi-turn context.
    """
    start_time = time.time()
    try:
        analysis = await analyze_task_async(request, router)
        logger.info(f"Task classified as {analysis.task_type} (Fallback: {analysis.is_fallback})")

        orchestrator = AgentOrchestrator(router)
        history_dicts = [{"role": h.role, "content": h.content} for h in request.history]
        final_output, trace = await orchestrator.run_async(
            request.query,
            analysis.task_type,
            history=history_dicts,
            file_paths=request.file_paths or [],
        )

        execution_time = int((time.time() - start_time) * 1000)

        return TaskResponse(
            status="success",
            final_output=final_output,
            generated_files=[],
            agent_trace=trace,
            execution_time_ms=execution_time,
            metadata={"classification": analysis.model_dump()}
        )
    except Exception as e:
        logger.error(f"Error in processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────────────────────────────────────
# SSE STREAMING (used by chat)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/stream")
async def api_stream_task(request: Request):
    """
    SSE endpoint for real-time streaming responses.
    Accepts: { query, history[], file_paths[] }
    Streams token chunks as SSE events. Sends [DONE] as final event.
    """
    body = await request.json()
    query = body.get("query", "")
    history = body.get("history", [])
    file_paths = body.get("file_paths", [])
    document_ids = body.get("active_document_ids", [])
    use_active_documents = body.get("use_active_documents", True)
    logger.info(
        "/stream received: query='%s' document_ids=%s use_active_documents=%s history_len=%s",
        query[:60], document_ids, use_active_documents, len(history)
    )

    async def event_generator():
        try:
            import asyncio
            from pathlib import Path as _Path

            # Ensure a new chat upload is indexable before its first answer.
            # Subsequent turns use the same stable IDs and therefore stay in
            # the conversation's document scope even after the composer clears.
            active_document_ids = []
            active_records = []
            for document_id in dict.fromkeys(document_ids if use_active_documents else []):
                record = get_document(document_id)
                if record is None:
                    logger.warning("Unknown active document ID: %s", document_id)
                    continue
                try:
                    if not record.get("indexed"):
                        index_registered_document(record)
                    active_document_ids.append(document_id)
                    active_records.append(record)
                except Exception as exc:
                    logger.error("Could not prepare %s: %s", record["name"], exc)

            # Chat previously treated an image as OCR text.  Route image
            # questions to the local multimodal model instead.
            image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
            image_path = next(
                (Path(fp) for fp in file_paths if Path(fp).suffix.lower() in image_exts),
                next((Path(record["path"]) for record in active_records
                      if Path(record["path"]).suffix.lower() in image_exts), None),
            )
            if use_active_documents and image_path and image_path.exists():
                from vision.analyzer import analyze_image_async
                result = await analyze_image_async(str(image_path), prompt=query, router=router)
                yield {"data": json.dumps({"token": result})}
                yield {"data": "[DONE]"}
                return

            # The streaming endpoint is also the chat endpoint.  Delegate
            # coding requests that name an attached local workspace to the
            # existing sandboxed coding orchestrator instead of the RAG chat.
            workspace = next((fp for fp in file_paths if Path(fp).is_dir()), None)
            if workspace is None:
                workspace = next(
                    (
                        fp for fp in file_paths
                        if Path(fp).is_absolute() and not Path(fp).suffix
                    ),
                    None,
                )
            if workspace is None:
                workspace = AgentOrchestrator(router)._extract_workspace(query)
            coding_request = bool(__import__("re").search(
                r"\b(write|create|build|generate|debug|fix|run|execute)\b.*\b(code|script|program|app|function|project|file|website|webpage|html|css|javascript|typescript|json|markdown)\b",
                query, __import__("re").IGNORECASE,
            ))
            if workspace and coding_request:
                orchestrator = AgentOrchestrator(router)
                workspace_query = f'{query}\n\nWorkspace: "{workspace}"'
                result, _ = await orchestrator.run_async(
                    workspace_query, TaskType.CODING, history=history, file_paths=[]
                )
                yield {"data": json.dumps({"token": result})}
                yield {"data": "[DONE]"}
                return

            # ── Track A: Extract text from newly uploaded files ───────────────
            # Keep to 1500 words max — qwen2.5:3b has 8K context; with prompt
            # overhead, 1500 words ≈ 2250 tokens, leaving plenty of room.
            WORDS_PER_FILE = 1500
            TEXT_EXTS = {".txt", ".md", ".csv", ".json"}
            file_blocks = []

            if file_paths and use_active_documents:
                from tools.vision_tool import extract_text

                for fp in file_paths:
                    p = _Path(fp)
                    if not p.exists():
                        logger.warning(f"File not found: {fp}")
                        continue
                    try:
                        ext = p.suffix.lower()
                        if ext in TEXT_EXTS:
                            raw = p.read_text(encoding="utf-8", errors="ignore")
                        else:
                            loop = asyncio.get_running_loop()
                            raw = await loop.run_in_executor(
                                None, extract_text, fp
                            )
                        # Hard-truncate at word level
                        words = raw.split()
                        truncated = " ".join(words[:WORDS_PER_FILE])
                        if len(words) > WORDS_PER_FILE:
                            truncated += f"\n[... {len(words)-WORDS_PER_FILE} more words not shown ...]"
                        file_blocks.append(f"[FILE: {p.name}]\n{truncated}")
                        logger.info(f"Loaded {min(len(words), WORDS_PER_FILE)}/{len(words)} words from {p.name}")
                    except Exception as ex:
                        logger.error(f"Text extraction failed for {fp}: {ex}")

            # ── Track B: Semantic retrieval from ChromaDB (previously indexed) ─
            kb_block = ""
            if use_active_documents:
                try:
                    from knowledge_base.retrieve import search_knowledge_base, format_for_prompt
                    kb_results = search_knowledge_base(
                        query, k=4, document_ids=active_document_ids or None
                    )
                    if kb_results:
                        kb_block = format_for_prompt(kb_results)
                        logger.info(f"Retrieved {len(kb_results)} chunks from ChromaDB")
                except Exception as kb_err:
                    logger.warning(f"ChromaDB retrieval skipped: {kb_err}")

            # ── Build the enriched prompt (no "file"/"document" language) ─────
            # Small models (qwen2.5:3b) refuse when they see "file"/"attached"/
            # "document" in prompts. We present the extracted text as plain
            # reading-comprehension context — they always follow this format.
            enriched_query = query
            context_parts = []

            if file_blocks:
                # Strip the "[FILE: name]" header — just use the raw text
                plain_texts = []
                for block in file_blocks:
                    # block is "[FILE: name]\ntext..." — drop the first line
                    lines = block.split("\n", 1)
                    plain_texts.append(lines[1] if len(lines) > 1 else block)
                context_parts.extend(plain_texts)

            if kb_block and kb_block != "(no relevant company documents found)":
                context_parts.append(kb_block)

            # When the user attached documents, absence of a match must not
            # trigger a search over the shared knowledge base.
            if active_document_ids and not context_parts:
                context_parts.append("No information relevant to the instruction was found in the active uploaded sources.")

            if context_parts:
                combined = "\n\n".join(context_parts)
                enriched_query = (
                    f"TEXT:\n{combined}\n\n"
                    f"Instruction: {query}"
                )

            # ── Build messages ────────────────────────────────────────────────
            system_content = (
                "You are VAJRA, a precise question-answering assistant. "
                "A TEXT passage is given to you. Read it and follow the Instruction exactly. "
                "Answer only from the TEXT. Do not mention files, emails, or attachments."
                if use_active_documents else
                "You are VAJRA, a precise general-purpose reasoning assistant. "
                "Answer the user's question directly using your knowledge."
            )

            messages = [{"role": "system", "content": system_content}]
            for h in history:
                role = h.get("role", "user")
                content = h.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": enriched_query})


            # ── Stream tokens ─────────────────────────────────────────────────
            model_name = router.get_model_for_task(TaskType.REASONING)
            async for chunk in router.chat_stream_async(model_name, messages):
                yield {"data": json.dumps({"token": chunk})}

            yield {"data": "[DONE]"}

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"error": str(e)})}





    return EventSourceResponse(event_generator())

# ─────────────────────────────────────────────────────────────────────────────
# STATIC FRONTEND (production build)
# ─────────────────────────────────────────────────────────────────────────────

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static_frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

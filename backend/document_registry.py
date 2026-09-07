"""Persistent, local registry for uploaded chat documents.

The registry deliberately stores only metadata and paths inside the Vajra
workspace.  It gives the UI a stable document identity instead of using a
filename (which is neither unique nor safe as a retrieval key).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(os.getenv("VAJRA_WORKSPACE", Path(__file__).resolve().parents[1]))
UPLOAD_DIR = WORKSPACE / "uploads"
REGISTRY_PATH = UPLOAD_DIR / "document_registry.json"


def _load() -> dict[str, dict]:
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(records: dict[str, dict]) -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temp = REGISTRY_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(records, indent=2), encoding="utf-8")
    temp.replace(REGISTRY_PATH)


def register_upload(original_name: str, path: Path, size: int | None = None) -> dict:
    document_id = str(uuid.uuid4())
    record = {
        "document_id": document_id,
        "name": original_name,
        "path": str(path.resolve()),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size": size,
        "indexed": False,
        "shared": False,
    }
    records = _load()
    records[document_id] = record
    _save(records)
    return record


def get_document(document_id: str) -> dict | None:
    return _load().get(document_id)


def find_by_path(path: str) -> dict | None:
    resolved = str(Path(path).resolve())
    return next((record for record in _load().values() if record["path"] == resolved), None)


def mark_indexed(document_id: str, domain: str | None = None, shared: bool = False) -> None:
    records = _load()
    if document_id in records:
        records[document_id]["indexed"] = True
        if domain:
            records[document_id]["domain"] = domain
        if shared:
            records[document_id]["shared"] = True
        _save(records)


def list_documents(shared_only: bool = False) -> list[dict]:
    """Return local uploads newest first; never expose unrelated filesystem paths."""
    records = _load().values()
    if shared_only:
        records = [record for record in records if record.get("shared")]
    return sorted(records, key=lambda record: record.get("uploaded_at", ""), reverse=True)


def list_all_documents() -> list[dict]:
    """Return ALL uploaded documents regardless of shared/indexed status (newest first).
    Used by the database UI so files appear immediately after upload."""
    records = list(_load().values())
    return sorted(records, key=lambda r: r.get("uploaded_at", ""), reverse=True)


def delete_document(document_id: str) -> bool:
    """Remove a document record from the registry. Returns True if found and deleted."""
    records = _load()
    if document_id not in records:
        return False
    del records[document_id]
    _save(records)
    return True


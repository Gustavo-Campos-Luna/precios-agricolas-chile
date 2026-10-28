"""Persistencia atómica y recibos de procedencia sin credenciales."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def atomic_write(path: str | Path, payload: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".partial-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def write_json(path: str | Path, value: object) -> Path:
    return atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n").encode())


def receipt(path: str | Path, *, url: str, source: str, **metadata) -> dict:
    path = Path(path)
    result = {
        "source": source, "url": url, "path": str(path),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size, **metadata,
    }
    write_json(path.with_suffix(path.suffix + ".manifest.json"), result)
    return result

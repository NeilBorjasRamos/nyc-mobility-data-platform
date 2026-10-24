"""Local coordination and atomic file replacement."""

import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


@contextmanager
def writer_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "writer.lock"
    # FileExistsError happens before finally: never remove another writer's lock.
    with path.open("x") as lock:
        lock.write(json.dumps({"pid": os.getpid(), "created_at": datetime.now(UTC).isoformat()}))
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, default=str, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)

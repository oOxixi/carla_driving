"""Atomic lifecycle records for reproducible evidence runs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class RunContext:
    run_id: str
    root: Path
    manifest_path: Path
    metrics_dir: Path
    logs_dir: Path
    media_dir: Path


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temp, path)


def begin_run(output_root: Path, metadata: dict[str, object]) -> RunContext:
    now = datetime.now(timezone.utc)
    run_id = f"{now:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    root = output_root / "runs" / run_id
    context = RunContext(
        run_id,
        root,
        root / "run_manifest.json",
        root / "metrics",
        root / "logs",
        root / "media",
    )
    for directory in (context.metrics_dir, context.logs_dir, context.media_dir):
        directory.mkdir(parents=True, exist_ok=False)
    _write_atomic(
        context.manifest_path,
        {
            **metadata,
            "run_id": run_id,
            "started_at": now.isoformat(),
            "status": "RUNNING",
            "failure_reason": None,
        },
    )
    return context


def finish_run(
    context: RunContext, status: str, failure_reason: str | None
) -> None:
    payload = json.loads(context.manifest_path.read_text(encoding="utf-8"))
    payload.update(
        status=status,
        failure_reason=failure_reason,
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    _write_atomic(context.manifest_path, payload)


__all__ = ["RunContext", "begin_run", "finish_run"]

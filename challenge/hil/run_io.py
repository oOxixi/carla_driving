"""Run directory layout, atomic writers, and the per-run evidence manifest."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4

from .identity import CandidateIdentity, sha256_file


def new_run_id(prefix: str = "b3") -> str:
    now = datetime.now(timezone.utc)
    return f"{prefix}-{now:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def write_json(path: str | Path, payload: object) -> Path:
    target = Path(path)
    _write_atomic(target, json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return target


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(dict(row), ensure_ascii=False, allow_nan=False)
        for row in rows
    ]
    _write_atomic(target, "".join(line + "\n" for line in lines))
    return target


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as stream:
        for number, raw in enumerate(stream, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: invalid JSON") from error
            if not isinstance(payload, dict):
                raise TypeError(f"{path}:{number}: record must be an object")
            records.append(payload)
    return records


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def write_csv(
    path: str | Path,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(list(columns))
        for row in rows:
            unknown = set(row) - set(columns)
            if unknown:
                raise ValueError(f"row has columns outside the frozen schema: {sorted(unknown)}")
            writer.writerow([_format_cell(row.get(column)) for column in columns])
    os.replace(temp, target)
    return target


class RunDir:
    """`runs/<run_id>/` evidence root for one measurement run."""

    def __init__(self, root: str | Path, run_id: str | None = None) -> None:
        self.run_id = run_id or new_run_id()
        self.root = Path(root).resolve() / self.run_id
        if self.root.exists():
            raise FileExistsError(f"run directory already exists: {self.root}")
        for name in ("raw", "stability_logs", "failure_cases", "schema", "logs"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def write_hardware_env(self, payload: Mapping[str, Any]) -> Path:
        return write_json(self.path("hardware_env.json"), dict(payload))

    def build_manifest(
        self,
        *,
        identity: CandidateIdentity,
        claim_scope: str,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        files: dict[str, dict[str, Any]] = {}
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            if path.name == "measurement_manifest.json":
                continue
            relative = path.relative_to(self.root).as_posix()
            files[relative] = {
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        manifest = {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "claim_scope": claim_scope,
            "identity": identity.to_dict(),
            "file_count": len(files),
            "files": files,
        }
        if extra:
            manifest.update(dict(extra))
        write_json(self.path("measurement_manifest.json"), manifest)
        return manifest


__all__ = [
    "RunDir",
    "new_run_id",
    "write_json",
    "read_json",
    "write_jsonl",
    "read_jsonl",
    "write_csv",
]

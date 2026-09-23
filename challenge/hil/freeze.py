"""Freeze a request set into a self-contained replay snapshot.

B1's formal D1/D2 deliveries live under the git-ignored ``artifacts/`` tree, so
they can move or change without any commit.  A frozen snapshot gives B3 (and
B2, which must recompute our numbers) one immutable input baseline.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .groups import normalize_group
from .identity import sha256_file
from .replay import ReplayCase, load_replay_cases
from .run_io import write_json, write_jsonl


SNAPSHOT_SCHEMA_VERSION = "1.0"


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _extension(path: str | None) -> str:
    if not path:
        return ".bin"
    suffix = Path(path).suffix
    return suffix if suffix else ".bin"


def freeze_snapshot(
    *,
    delivery_root: str | Path | None,
    out_root: str | Path,
    name: str,
    requests_path: str | Path | None = None,
    repo_root: str | Path | None = None,
    limit: int | None = None,
    copy_rgb: bool = True,
) -> dict[str, Any]:
    if not name or any(character in name for character in "\\/:*?\"<>|"):
        raise ValueError("snapshot name must be a plain directory name")
    cases, info = load_replay_cases(
        delivery_root=delivery_root,
        requests_path=requests_path,
        repo_root=repo_root,
        limit=limit,
    )
    target = Path(out_root).resolve() / name
    rgb_dir = target / "rgb"
    target.mkdir(parents=True, exist_ok=True)
    rgb_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    copied = 0
    for case in cases:
        rgb_relative: str | None = None
        if copy_rgb and case.rgb_resolved and case.rgb_path and case.rgb_sha256:
            destination = rgb_dir / f"{case.rgb_sha256}{_extension(case.rgb_path)}"
            if not destination.exists():
                shutil.copyfile(case.rgb_path, destination)
            rgb_relative = f"rgb/{destination.name}"
            copied += 1
        records.append(
            {
                "case_id": case.case_id,
                "sample_id": case.sample_id,
                "scenario_id": case.scenario_id,
                "source_file": case.source_file,
                "request": case.request,
                "request_sha256": _canonical_sha256(case.request),
                "rgb_sha256": case.rgb_sha256,
                "rgb_path": rgb_relative,
                "rgb_resolved_at_freeze_time": case.rgb_resolved,
                "rgb_source": case.rgb_source,
                "teacher_plan": case.teacher_plan,
                "teacher_plan_sha256": (
                    _canonical_sha256(case.teacher_plan) if case.teacher_plan else None
                ),
                # Persist B2's group label unchanged (None when absent) so a
                # frozen snapshot keeps the evaluation grouping with the inputs.
                "group": case.group,
            }
        )
    cases_path = write_jsonl(target / "cases.jsonl", records)
    digests = sorted(record["request_sha256"] for record in records)
    set_digest = _canonical_sha256(digests)
    manifest = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "name": name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "delivery_root": str(delivery_root) if delivery_root else None,
            "requests_path": info["requests_path"],
            "repo_root": str(repo_root) if repo_root else None,
            "source_preference": info["source_preference"],
        },
        "counts": {
            "cases": len(records),
            "rgb_resolved": sum(1 for record in records if record["rgb_path"]),
            "rgb_copied": copied,
            "teacher_plans": sum(1 for record in records if record["teacher_plan"]),
        },
        "case_set_digest_sha256": set_digest,
        "files": {
            "cases.jsonl": {
                "size_bytes": cases_path.stat().st_size,
                "sha256": sha256_file(cases_path),
            }
        },
        "notes": (
            "Replay inputs are frozen here so later runs and B2 recomputation use "
            "byte-identical requests; the RGB copies are content-addressed by SHA256."
        ),
    }
    if not copy_rgb:
        manifest["notes"] += " RGB files were NOT copied (--no-copy-rgb)."
    write_json(target / "manifest.json", manifest)
    return {"snapshot": str(target), "manifest": manifest}


def load_frozen_snapshot(snapshot_dir: str | Path) -> tuple[list[ReplayCase], dict[str, Any]]:
    """Read a snapshot back into replay cases, verifying every recorded hash."""
    root = Path(snapshot_dir).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    cases_path = root / "cases.jsonl"
    recorded = manifest["files"]["cases.jsonl"]["sha256"]
    actual = sha256_file(cases_path)
    if recorded != actual:
        raise ValueError(f"snapshot cases.jsonl changed: {actual} != {recorded}")
    cases: list[ReplayCase] = []
    with cases_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            request = record["request"]
            digest = _canonical_sha256(request)
            if digest != record["request_sha256"]:
                raise ValueError(
                    f"snapshot request drifted for {record.get('case_id')}: "
                    f"{digest} != {record['request_sha256']}"
                )
            rgb_path = None
            resolved = False
            if record.get("rgb_path"):
                candidate = root / record["rgb_path"]
                if candidate.is_file():
                    rgb_path = str(candidate)
                    resolved = True
                    if record.get("rgb_sha256") and sha256_file(candidate) != record["rgb_sha256"]:
                        resolved = False
            cases.append(
                ReplayCase(
                    case_id=record["case_id"],
                    sample_id=record["sample_id"],
                    scenario_id=record["scenario_id"],
                    request={
                        **request,
                        **({"rgb_ref": rgb_path} if resolved else {}),
                    },
                    teacher_plan=record.get("teacher_plan"),
                    rgb_path=rgb_path,
                    rgb_sha256=record.get("rgb_sha256"),
                    rgb_resolved=resolved,
                    rgb_source="frozen_snapshot",
                    source_file=str(cases_path),
                    group=normalize_group(record.get("group")),
                )
            )
    info = {
        "snapshot": str(root),
        "name": manifest.get("name"),
        "case_set_digest_sha256": manifest.get("case_set_digest_sha256"),
        "cases": len(cases),
        "rgb_resolved": sum(1 for case in cases if case.rgb_resolved),
    }
    return cases, info


__all__ = ["freeze_snapshot", "load_frozen_snapshot", "SNAPSHOT_SCHEMA_VERSION"]

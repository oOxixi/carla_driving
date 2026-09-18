"""Provenance pins that every B3 run must carry.

The Teacher baseline is the only frozen identity the challenge track has so
far (``challenge/teacher_baseline_manifest.json`` plus the
``teacher-baseline-v1`` tag).  Recording it with each measurement is what lets
a later reader answer "which Teacher was this compared against".
"""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from .identity import UNRESOLVED, sha256_file
from .run_io import read_json


TEACHER_BASELINE_MANIFEST = "challenge/teacher_baseline_manifest.json"
TEACHER_BASELINE_TAG = "teacher-baseline-v1"
TEACHER_PINNED_MANIFEST_V4 = "challenge/teacher_pinned_manifest_v4.json"
TEACHER_BASELINE_TAG_V4 = "teacher-baseline-v4"


def resolve_tag(repo_root: str | Path, tag: str = TEACHER_BASELINE_TAG) -> dict[str, Any]:
    """Resolve a local tag to a commit SHA without touching the network."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-list", "-n", "1", tag],
            capture_output=True,
            text=True,
            timeout=20.0,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {
            "tag": tag,
            "sha": UNRESOLVED,
            "reason": f"{type(error).__name__}: {error}",
        }
    sha = completed.stdout.strip()
    return {"tag": tag, "sha": sha or UNRESOLVED, "reason": None if sha else "empty"}


def _load_pin(
    repo: Path,
    *,
    label: str,
    manifest_relative: str,
    default_tag: str,
    git_key: str,
    fingerprint_key: str,
) -> dict[str, Any]:
    manifest_path = repo / manifest_relative
    pin: dict[str, Any] = {
        "label": label,
        "manifest_path": manifest_relative,
        "status": "UNRESOLVED",
        "manifest_sha256": None,
        "baseline_id": default_tag,
        "git_sha": UNRESOLVED,
        "model_id": UNRESOLVED,
        "model_revision": UNRESOLVED,
        "artifact_fingerprint_sha256": UNRESOLVED,
    }
    if not manifest_path.is_file():
        return pin
    payload = read_json(manifest_path)
    pin.update(
        {
            "status": "PINNED",
            "manifest_sha256": sha256_file(manifest_path),
            "baseline_id": str(
                payload.get("baseline_id")
                or payload.get("teacher_profile")
                or default_tag
            ),
            "git_sha": str(payload.get(git_key, UNRESOLVED)),
            "model_id": str(payload.get("model_id", UNRESOLVED)),
            "model_revision": str(payload.get("model_revision", UNRESOLVED)),
            "artifact_fingerprint_sha256": str(
                payload.get(fingerprint_key, UNRESOLVED)
            ),
            "verification_status": payload.get("verification_status"),
            "source_branch": payload.get("source_branch"),
            "input_contract": payload.get("input_contract"),
            "output_contract": payload.get("output_contract"),
            "serving": payload.get("serving"),
            "dtype": payload.get("dtype"),
        }
    )
    tag = resolve_tag(repo, default_tag)
    pin["git_tag"] = tag
    if tag["sha"] != UNRESOLVED and tag["sha"] != pin["git_sha"]:
        pin["status"] = "TAG_MISMATCH"
    return pin


def teacher_baselines(repo_root: str | Path) -> dict[str, Any]:
    """Read every pinned Teacher manifest and cross-check it against its tag.

    Two pins currently exist: ``teacher-baseline-v1`` (identity + contracts) and
    ``teacher-baseline-v4`` (data-semantic governance).  Both describe the same
    model, so a run records both and asserts that their model identities agree;
    recording only one would silently hide a governance change.
    """
    repo = Path(repo_root).resolve()
    v1 = _load_pin(
        repo,
        label="v1",
        manifest_relative=TEACHER_BASELINE_MANIFEST,
        default_tag=TEACHER_BASELINE_TAG,
        git_key="git_sha",
        fingerprint_key="artifact_fingerprint_sha256",
    )
    v4 = _load_pin(
        repo,
        label="v4",
        manifest_relative=TEACHER_PINNED_MANIFEST_V4,
        default_tag=TEACHER_BASELINE_TAG_V4,
        git_key="teacher_git_sha",
        fingerprint_key="model_artifact_sha256",
    )
    pinned = [pin for pin in (v1, v4) if pin["status"] in {"PINNED", "TAG_MISMATCH"}]
    fields = ("model_id", "model_revision", "artifact_fingerprint_sha256")
    consistent = bool(pinned) and all(
        len({pin[field] for pin in pinned}) == 1 for field in fields
    )
    return {
        "v1": v1,
        "v4": v4,
        "active": "v4" if v4["status"] != "UNRESOLVED" else "v1",
        "model_identity_consistent": consistent,
        "model_identity_fields": list(fields),
    }


def teacher_baseline(repo_root: str | Path) -> dict[str, Any]:
    """Backwards-compatible accessor: the active pin."""
    baselines = teacher_baselines(repo_root)
    return baselines[baselines["active"]]


__all__ = [
    "TEACHER_BASELINE_MANIFEST",
    "TEACHER_BASELINE_TAG",
    "TEACHER_PINNED_MANIFEST_V4",
    "TEACHER_BASELINE_TAG_V4",
    "teacher_baselines",
    "teacher_baseline",
    "resolve_tag",
]

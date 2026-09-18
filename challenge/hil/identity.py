"""Candidate identity (the five mandatory identifiers) and hashing helpers."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping


IDENTITY_FIELDS: tuple[str, ...] = (
    "git_sha",
    "model_id",
    "model_sha256",
    "dataset_version",
    "config_id",
)

UNRESOLVED = "UNRESOLVED"
_SHA1_RE = re.compile(r"[0-9a-fA-F]{40}")


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            block = stream.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def git_head(repo: str | Path) -> str:
    """Return the current commit SHA, or UNRESOLVED when git cannot answer."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=20.0,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return UNRESOLVED
    value = completed.stdout.strip()
    return value if _SHA1_RE.fullmatch(value) else UNRESOLVED


@dataclass(frozen=True, slots=True)
class CandidateIdentity:
    """Identity of the artifact under test.

    ``UNRESOLVED`` is allowed so the harness can run before A2/A3 deliver; it
    is never allowed to appear in a report that claims a gate result.
    """

    git_sha: str = UNRESOLVED
    model_id: str = UNRESOLVED
    model_sha256: str = UNRESOLVED
    dataset_version: str = UNRESOLVED
    config_id: str = UNRESOLVED
    gate_status: str = "NOT_PROVIDED"
    weights_manifest: str | None = None

    def __post_init__(self) -> None:
        for name in IDENTITY_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"identity field {name} must be a non-empty string")
        if self.git_sha != UNRESOLVED and not _SHA1_RE.fullmatch(self.git_sha):
            raise ValueError("git_sha must be a full 40-character Git SHA or UNRESOLVED")
        if self.model_sha256 != UNRESOLVED and not re.fullmatch(r"[0-9a-fA-F]{64}", self.model_sha256):
            raise ValueError("model_sha256 must be a 64-character hex digest or UNRESOLVED")

    @property
    def complete(self) -> bool:
        return all(getattr(self, name) != UNRESOLVED for name in IDENTITY_FIELDS)

    def missing(self) -> tuple[str, ...]:
        return tuple(name for name in IDENTITY_FIELDS if getattr(self, name) == UNRESOLVED)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["complete"] = self.complete
        payload["missing"] = list(self.missing())
        return payload


def identity_from_weight_manifest(
    weights: str | Path,
    manifest_path: str | Path,
) -> CandidateIdentity:
    """Read A3's weight manifest and verify its digest against the real file.

    The manifest's self-reported hash is never trusted: the SHA256 is recomputed
    from the artifact on disk.
    """
    path = Path(weights)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise ValueError("weight manifest must be a JSON object")
    actual = sha256_file(path)
    reported = str(manifest.get("weights_sha256", ""))
    if reported and reported.lower() != actual.lower():
        raise ValueError(
            f"weight manifest SHA256 mismatch: manifest={reported} actual={actual}"
        )
    return CandidateIdentity(
        git_sha=str(manifest.get("git_sha") or UNRESOLVED),
        model_id=str(manifest.get("model_id") or UNRESOLVED),
        model_sha256=actual,
        dataset_version=str(manifest.get("dataset_version") or UNRESOLVED),
        config_id=str(manifest.get("config_id") or UNRESOLVED),
        gate_status=str(manifest.get("gate_status") or "NOT_PROVIDED"),
        weights_manifest=str(manifest_path),
    )


def identity_from_artifact(
    artifact: str | Path,
    *,
    model_id: str = UNRESOLVED,
    config_id: str = UNRESOLVED,
    dataset_version: str = UNRESOLVED,
    git_sha: str = UNRESOLVED,
) -> CandidateIdentity:
    return CandidateIdentity(
        git_sha=git_sha,
        model_id=model_id,
        model_sha256=sha256_file(artifact),
        dataset_version=dataset_version,
        config_id=config_id,
    )


__all__ = [
    "IDENTITY_FIELDS",
    "UNRESOLVED",
    "CandidateIdentity",
    "sha256_file",
    "git_head",
    "identity_from_weight_manifest",
    "identity_from_artifact",
]

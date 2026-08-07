"""Verify immutable release inputs before the offline CUDA 13.2 wheel build."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def verify_source(source: Path, lock: dict[str, object]) -> dict[str, object]:
    archive = lock.get("source_archive")
    commit = lock.get("commit")
    if not isinstance(archive, dict) or not isinstance(commit, str):
        raise ValueError("source lock must contain commit and source_archive")
    required = ("filename", "bytes", "sha256", "generated_from_commit")
    if any(key not in archive for key in required):
        raise ValueError("source_archive lock is incomplete")
    if archive["generated_from_commit"] != commit:
        raise ValueError("source archive provenance commit does not match lock commit")
    if source.name != archive["filename"] or commit not in source.name:
        raise ValueError("source archive filename does not identify the locked commit")
    if source.stat().st_size != archive["bytes"]:
        raise ValueError("source archive byte size does not match lock")
    if _sha256(source) != archive["sha256"]:
        raise ValueError("source archive SHA256 does not match lock")
    return {"commit": commit, "source_sha256": archive["sha256"]}


def verify_wheelhouse(wheelhouse: Path, lock: dict[str, object]) -> dict[str, object]:
    files = lock.get("files")
    resolved = lock.get("resolved_files")
    excluded = lock.get("excluded_candidates")
    if not all(isinstance(value, list) for value in (files, resolved, excluded)):
        raise ValueError("wheelhouse lock must contain files, resolved_files, and excluded_candidates")
    expected = {
        item["path"]: item
        for item in files
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if len(expected) != len(files) or len(expected) != lock.get("file_count"):
        raise ValueError("wheelhouse lock has duplicate or incomplete file entries")
    actual = {path.name for path in wheelhouse.iterdir() if path.is_file()}
    if actual != set(expected):
        raise ValueError("wheelhouse file set does not match lock")
    if sum(path.stat().st_size for path in wheelhouse.iterdir() if path.is_file()) != lock.get("total_bytes"):
        raise ValueError("wheelhouse total byte size does not match lock")
    for name, entry in expected.items():
        path = wheelhouse / name
        if path.stat().st_size != entry.get("bytes") or _sha256(path) != entry.get("sha256"):
            raise ValueError(f"wheelhouse hash mismatch: {name}")
    if len(set(resolved)) != len(resolved) or not set(resolved).issubset(expected):
        raise ValueError("resolved wheel list is invalid")
    if actual - set(resolved) != set(excluded):
        raise ValueError("excluded wheel candidates do not exactly account for wheelhouse extras")
    return {
        "wheelhouse_files": len(expected),
        "resolved_files": len(resolved),
        "aggregate_manifest_sha256": lock.get("aggregate_manifest_sha256"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--wheelhouse-lock", type=Path, required=True)
    args = parser.parse_args()
    result = verify_source(args.source, _load_json(args.source_lock))
    result.update(verify_wheelhouse(args.wheelhouse, _load_json(args.wheelhouse_lock)))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

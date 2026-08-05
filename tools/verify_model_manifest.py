"""Verify that one staged model profile exactly matches its release manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_manifest_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("manifest file path must be a non-empty string")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in value:
        raise ValueError(f"unsafe manifest file path: {value}")
    return candidate.as_posix()


def verify_profile(manifest_path: Path, root: Path, profile: str) -> dict[str, object]:
    """Return the sole verified profile entry or raise ``ValueError`` on drift."""
    payload: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    models = payload.get("models")
    if not isinstance(models, list):
        raise ValueError("manifest models must be a list")
    matches = [item for item in models if isinstance(item, dict) and item.get("profile") == profile]
    if len(matches) != 1:
        raise ValueError(f"manifest must contain one profile entry: {profile}")
    entry = matches[0]
    files = entry.get("files")
    if not isinstance(files, list):
        raise ValueError(f"manifest profile files must be a list: {profile}")
    expected: dict[str, dict[str, object]] = {}
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("manifest file entry must be an object")
        relative = _safe_manifest_path(item.get("path"))
        if relative in expected:
            raise ValueError(f"duplicate manifest file entry: {relative}")
        expected[relative] = item
    if not root.is_dir():
        raise ValueError(f"model root does not exist: {root}")
    actual = {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file()
    }
    if set(actual) != set(expected):
        raise ValueError("model file set does not match manifest")
    for relative, path in actual.items():
        metadata = expected[relative]
        if path.stat().st_size != metadata.get("bytes"):
            raise ValueError(f"byte size mismatch: {relative}")
        if sha256_file(path) != metadata.get("sha256"):
            raise ValueError(f"SHA256 mismatch: {relative}")
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    entry = verify_profile(args.manifest, args.root, args.profile)
    print(json.dumps({
        "profile": args.profile,
        "revision": entry.get("revision"),
        "quantization": entry.get("quantization"),
        "kernel": entry.get("kernel", entry.get("required_linear_kernel")),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

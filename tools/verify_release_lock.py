"""Verify one hashed staged release asset before it is consumed by a build."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_asset(lock_path: Path, root: Path, key: str) -> Path:
    metadata = json.loads(lock_path.read_text(encoding="utf-8"))[key]
    path = root / metadata["filename"]
    if not path.is_file():
        raise ValueError(f"locked asset is missing: {path}")
    if path.stat().st_size != metadata["bytes"]:
        raise ValueError(f"locked asset byte size mismatch: {path.name}")
    if sha256_file(path) != metadata["sha256"]:
        raise ValueError(f"locked asset SHA256 mismatch: {path.name}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()
    print(verify_asset(args.lock, args.root, args.key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

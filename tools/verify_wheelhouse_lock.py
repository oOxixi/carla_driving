"""Reject any wheelhouse drift from its frozen complete manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_wheelhouse_lock import sha256_file


def verify_wheelhouse(lock_path: Path, root: Path) -> None:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    expected = {item["path"]: item for item in lock["files"]}
    actual = {path.name: path for path in root.iterdir() if path.is_file() and path.suffix == ".whl"}
    if set(actual) != set(expected):
        raise ValueError("wheelhouse file set does not match lock")
    for name, path in actual.items():
        metadata = expected[name]
        if path.stat().st_size != metadata["bytes"] or sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"wheelhouse hash mismatch: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    args = parser.parse_args()
    verify_wheelhouse(args.lock, args.wheelhouse)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

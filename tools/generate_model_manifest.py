"""Generate per-file and aggregate SHA-256 metadata for a local model."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--license", required=True, dest="license_name")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.model_dir.resolve()
    files = []
    aggregate = hashlib.sha256()
    for path in sorted(item for item in root.iterdir() if item.is_file()):
        digest = _sha256(path)
        relative = path.name
        size = path.stat().st_size
        files.append({
            "path": relative,
            "bytes": size,
            "sha256": digest,
        })
        aggregate.update(f"{digest}  {relative}\n".encode("utf-8"))
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_name": args.model_name,
        "license": args.license_name,
        "model_directory_at_validation": str(root),
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "aggregate_manifest_sha256": aggregate.hexdigest(),
        "files": files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        key: report[key]
        for key in (
            "model_name",
            "license",
            "file_count",
            "total_bytes",
            "aggregate_manifest_sha256",
        )
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

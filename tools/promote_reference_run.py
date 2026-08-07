"""Promote one completed, hash-verified runtime directory to reference evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def promote_reference_run(source: Path, destination: Path, hardware_label: str) -> None:
    manifest_path = source / "run_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"run manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") == "RUNNING":
        raise ValueError("cannot promote a RUNNING manifest")
    required = ("environment.json", "model_manifest.json", "metrics", "logs")
    missing = [name for name in required if not (source / name).exists()]
    if missing:
        raise FileNotFoundError("incomplete run evidence: " + ", ".join(missing))
    for relative, expected in manifest.get("files", {}).items():
        path = source / relative
        if not path.is_file():
            raise FileNotFoundError(f"manifest evidence missing: {relative}")
        if _sha256(path) != expected:
            raise ValueError(f"manifest hash mismatch: {relative}")
    if destination.exists():
        raise FileExistsError(f"reference destination already exists: {destination}")
    shutil.copytree(source, destination)
    readme = destination / "README.md"
    existing = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    readme.write_text(
        f"# {hardware_label}\n\nrun_id: `{manifest.get('run_id', 'unknown')}`  \n"
        f"status: `{manifest.get('status', 'unknown')}`\n\n{existing}", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--hardware-label", required=True)
    args = parser.parse_args()
    promote_reference_run(args.run_dir, args.destination, args.hardware_label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

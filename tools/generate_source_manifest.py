"""Hash all tracked and untracked Python source files in the repository."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def _git_files(root: Path, *args: str) -> list[str]:
    output = subprocess.check_output(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
    )
    return [line for line in output.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    paths = sorted(set(
        _git_files(root, "ls-files", "*.py")
        + _git_files(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "*.py",
        )
    ))
    aggregate = hashlib.sha256()
    files = []
    for relative in paths:
        path = root / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append({
            "path": relative.replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": digest,
        })
        aggregate.update(
            f"{digest}  {relative.replace(chr(92), '/')}\n".encode("utf-8")
        )
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            encoding="utf-8",
        ).strip(),
        "python_file_count": len(files),
        "aggregate_manifest_sha256": aggregate.hexdigest(),
        "files": files,
    }
    output = args.output
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "python_file_count": report["python_file_count"],
        "aggregate_manifest_sha256": report[
            "aggregate_manifest_sha256"
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

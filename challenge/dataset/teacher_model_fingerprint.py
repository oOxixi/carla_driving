#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LOCAL_METADATA_FILES = frozenset({".model_revision"})


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(root: Path, *, model_id: str, revision: str) -> dict:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"MODEL_DIR_NOT_FOUND={root}")

    files = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if ".cache" in rel.parts:
            continue
        if rel.as_posix() in LOCAL_METADATA_FILES:
            continue
        files.append(
            {
                "path": rel.as_posix(),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
        )

    canonical = json.dumps(
        files,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    artifact_sha = hashlib.sha256(canonical).hexdigest()

    payload = {
        "schema_version": "1.0",
        "fingerprint_method": (
            "SHA256(canonical JSON list of model artifact files; excludes "
            ".cache and local .model_revision metadata; "
            "sorted by path; each entry contains path,size_bytes,sha256)"
        ),
        "model_id": model_id,
        "model_revision": revision,
        "local_dir": str(root),
        "file_count": len(files),
        "model_artifact_sha256": artifact_sha,
        "files": files,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--model-id", default="Qwen/Qwen3.5-2B")
    parser.add_argument("--revision", required=True)
    parser.add_argument(
        "--output",
        default="artifacts/b1_teacher_pinned/teacher_model_manifest.json",
    )
    args = parser.parse_args()

    root = Path(args.model_dir).expanduser().resolve()
    try:
        payload = build_manifest(root, model_id=args.model_id, revision=args.revision)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("MODEL_ID=" + args.model_id)
    print("MODEL_REVISION=" + args.revision)
    print("MODEL_FILES=" + str(payload["file_count"]))
    print("MODEL_ARTIFACT_SHA256=" + payload["model_artifact_sha256"])
    print("MANIFEST=" + str(out))
    print("TEACHER_ARTIFACT_FINGERPRINT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a tracked-source snapshot for the challenge Student/runtime chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "challenge_source_runtime_preview_20261008"
ARCHIVE_NAME = "CHALLENGE_SOURCE_RUNTIME_PREVIEW_20261008.zip"

INCLUDED_ROOTS = (
    "challenge/benchmark/",
    "challenge/student/",
    "challenge/planner/",
    "challenge/quantization/",
    "challenge/runtime/",
    "challenge/horizon/",
    "challenge/hil/",
    "runtime/",
    "integration/",
    "interfaces/",
    "car_control_A/",
    "car_control_B/",
    "car_control_C/",
    "car_control_D/",
    "qwen_service/",
    "config/",
    "docker/",
    "scripts/",
    "tools/",
    "docs/architecture/modules/",
)

EXCLUDED_PREFIXES = (
    "challenge/hil/evidence/",
    "challenge/hil/dumps/",
    "challenge/dataset/",
    "challenge/distillation/releases/",
)

ROOT_FILES = {
    ".gitattributes",
    ".gitignore",
    "README.md",
    "requirements.txt",
    "pytest.ini",
    "pyproject.toml",
}

ALLOWED_SUFFIXES = {
    ".bat",
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".patch",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

FORBIDDEN_SUFFIXES = {
    ".bc",
    ".hbm",
    ".jpg",
    ".jpeg",
    ".mp3",
    ".npy",
    ".npz",
    ".onnx",
    ".png",
    ".pt",
    ".safetensors",
    ".tar",
    ".wav",
    ".zip",
}


def git(repo: Path, *arguments: str, binary: bool = False) -> str | bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), *arguments],
        text=not binary,
        encoding=None if binary else "utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_tracked_files(repo: Path) -> list[str]:
    payload = git(repo, "ls-files", "-z", binary=True)
    assert isinstance(payload, bytes)
    tracked = payload.decode("utf-8").split("\0")
    selected: list[str] = []
    for raw in tracked:
        if not raw:
            continue
        relative = raw.replace("\\", "/")
        path = repo / relative
        if not path.is_file():
            continue
        if any(relative.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        if relative not in ROOT_FILES and not any(
            relative.startswith(root) for root in INCLUDED_ROOTS
        ):
            continue
        suffix = path.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            continue
        special_name = path.name.startswith("Dockerfile") or path.name == ".env.example"
        if (
            relative not in ROOT_FILES
            and not special_name
            and suffix not in ALLOWED_SUFFIXES
        ):
            continue
        selected.append(relative)
    return sorted(set(selected))


def deterministic_zip(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
        allowZip64=True,
    ) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            with path.open("rb") as input_stream, archive.open(
                info, "w", force_zip64=True
            ) as output_stream:
                shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)


def verify_archive(package: Path, archive_path: Path) -> dict[str, Any]:
    expected = {
        path.relative_to(package).as_posix(): sha256_file(path)
        for path in package.rglob("*")
        if path.is_file()
    }
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC failure: {bad}")
        if set(archive.namelist()) != set(expected):
            raise RuntimeError("ZIP member list mismatch")
        for name, digest in expected.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise RuntimeError(f"ZIP member SHA256 mismatch: {name}")
    return {"files": len(expected), "crc": "PASS", "sha256": "PASS"}


def build(repo: Path, output: Path) -> dict[str, Any]:
    package = output / PACKAGE_ID
    archive_path = output / ARCHIVE_NAME
    archive_sha_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    staging = output / (PACKAGE_ID + ".tmp")
    if any(path.exists() for path in (package, archive_path, archive_sha_path, staging)):
        raise FileExistsError("source preview output already exists")
    staging.mkdir(parents=True)

    try:
        entries: list[dict[str, Any]] = []
        for relative in selected_tracked_files(repo):
            source = repo / relative
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            entries.append(
                {
                    "path": relative,
                    "size_bytes": destination.stat().st_size,
                    "sha256": sha256_file(destination),
                }
            )

        source_sha = str(git(repo, "rev-parse", "HEAD")).strip()
        source_branch = str(git(repo, "branch", "--show-current")).strip()
        manifest = {
            "schema_version": "1.0",
            "package_id": PACKAGE_ID,
            "status": "PRE_GATE_SOURCE_RUNTIME_PREVIEW",
            "formal_release": False,
            "source_git_sha": source_sha,
            "source_branch": source_branch,
            "file_count": len(entries),
            "files": entries,
            "excluded": [
                "model weights and ONNX",
                "training/calibration/independent-validation data",
                "generated evidence and caches",
                "compiled .bc/.hbm artifacts",
                "Docker image archive and media",
            ],
            "limitations": [
                "This is a source snapshot, not a runnable Final deployment package.",
                "Use the recipient-specific A2 ZIPs for candidate ONNX/INT8/NPY payloads.",
                "A4 must still deliver exact-RC compiled artifacts and Runtime; B3 must deliver J6P evidence.",
            ],
        }
        (staging / "SOURCE_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        (staging / "README.md").write_text(
            """# Challenge source/runtime preview

This archive contains the tracked Student, benchmark, quantization, runtime,
CARLA integration, control, interface, Docker-definition, script, and tooling
sources at the Git identity recorded in `SOURCE_MANIFEST.json`.

It deliberately excludes weights, ONNX, datasets, generated evidence, compiled
J6P artifacts, and Docker images. It is `PRE_GATE_SOURCE_RUNTIME_PREVIEW`, not a
Final deployment package.
""",
            encoding="utf-8",
            newline="\n",
        )
        checksum_paths = sorted(
            path for path in staging.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
        )
        (staging / "SHA256SUMS").write_text(
            "\n".join(
                f"{sha256_file(path)}  {path.relative_to(staging).as_posix()}"
                for path in checksum_paths
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        staging.replace(package)
        deterministic_zip(package, archive_path)
        verification = verify_archive(package, archive_path)
        archive_sha = sha256_file(archive_path)
        archive_sha_path.write_text(
            f"{archive_sha}  {archive_path.name}\n", encoding="ascii", newline="\n"
        )
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        if package.exists():
            shutil.rmtree(package, ignore_errors=True)
        archive_path.unlink(missing_ok=True)
        archive_sha_path.unlink(missing_ok=True)
        raise

    return {
        "package": str(package),
        "archive": str(archive_path),
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_sha256": archive_sha,
        "verification": verification,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(REPOSITORY_ROOT))
    parser.add_argument("--output", default="artifacts/submission")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = (repo / output).resolve()
    try:
        result = build(repo, output)
    except (FileExistsError, OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

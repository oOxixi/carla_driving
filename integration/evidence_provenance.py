"""Record the actual checkout, scenario bytes and runtime used by an experiment."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from importlib import metadata
import platform
from pathlib import Path
import subprocess
import sys


def _git(root: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, timeout=10,
    ).stdout


def collect_provenance(root: Path, scenario_path: str | None = None) -> dict[str, object]:
    """Keep HEAD separate from local changes; never infer a clean source version."""
    source: dict[str, object] = {"git_sha": "UNKNOWN", "dirty": None}
    try:
        source["git_sha"] = _git(root, "rev-parse", "HEAD").decode().strip()
        status = _git(root, "status", "--porcelain=v1", "-z")
        patch = _git(root, "diff", "HEAD", "--binary", "--no-ext-diff", "--ignore-cr-at-eol")
        untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
        changes = hashlib.sha256(patch)
        untracked_hashes = {}
        for name in sorted(filter(None, untracked.decode("utf-8").split("\0"))):
            path = root / name
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            untracked_hashes[name] = digest
            changes.update(name.encode() + b"\0" + digest.encode() + b"\0")
        source.update(
            dirty=bool(status),
            changes_sha256=changes.hexdigest(),
            status_porcelain=list(filter(None, status.decode("utf-8", errors="replace").split("\0"))),
            untracked_sha256=untracked_hashes,
        )
    except (OSError, UnicodeError, subprocess.SubprocessError) as error:
        source["error"] = type(error).__name__
    packages = {}
    for name in ("carla", "numpy", "Pillow", "torch", "onnxruntime", "jsonschema"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    config: dict[str, object] = {"path": scenario_path, "sha256": None}
    if scenario_path:
        path = Path(scenario_path)
        if not path.is_absolute():
            path = root / path
        try:
            config["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            config["error"] = type(error).__name__
    return {
        "schema_version": "1.0", "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": source, "scenario": config,
        "runtime": {
            "python": platform.python_version(), "executable": sys.executable,
            "platform": platform.platform(), "machine": platform.machine(),
            "hostname": platform.node(), "packages": packages,
        },
    }

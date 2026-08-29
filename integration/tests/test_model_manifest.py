import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.create_qwen_launch_logs import create_launch_logs
from tools.verify_model_manifest import verify_profile
from tools.verify_release_lock import verify_asset


ROOT = Path(__file__).resolve().parents[2]


def _manifest(path: Path, files: list[dict[str, object]]) -> Path:
    manifest = path / "manifest.json"
    manifest.write_text(json.dumps({"models": [{
        "profile": "qwen3vl-2b-int4",
        "revision": "f91db2369bd00e7ec20bf09b6a0080cdb26aefa5",
        "quantization": "gptq",
        "kernel": "MarlinLinearKernel",
        "files": files,
    }]}), encoding="utf-8")
    return manifest


def test_profile_verifier_accepts_exact_nested_tree_and_cli_reports_metadata(tmp_path: Path) -> None:
    root = tmp_path / "model"
    nested = root / "nested"
    nested.mkdir(parents=True)
    payload = b"verified"
    (nested / "config.json").write_bytes(payload)
    manifest = _manifest(tmp_path, [{
        "path": "nested/config.json",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }])

    assert verify_profile(manifest, root, "qwen3vl-2b-int4")["kernel"] == "MarlinLinearKernel"
    result = subprocess.run(
        [sys.executable, "tools/verify_model_manifest.py", "--manifest", str(manifest),
         "--root", str(root), "--profile", "qwen3vl-2b-int4"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout) == {
        "kernel": "MarlinLinearKernel",
        "profile": "qwen3vl-2b-int4",
        "quantization": "gptq",
        "revision": "f91db2369bd00e7ec20bf09b6a0080cdb26aefa5",
    }


@pytest.mark.parametrize("path", ["../config.json", "/config.json", "nested\\config.json"])
def test_profile_verifier_rejects_unsafe_manifest_paths(tmp_path: Path, path: str) -> None:
    root = tmp_path / "model"
    root.mkdir()
    manifest = _manifest(tmp_path, [{"path": path, "bytes": 0, "sha256": "0" * 64}])

    with pytest.raises(ValueError, match="unsafe manifest file path"):
        verify_profile(manifest, root, "qwen3vl-2b-int4")


def test_profile_verifier_rejects_duplicate_profile_entries(tmp_path: Path) -> None:
    root = tmp_path / "model"
    root.mkdir()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"models": [
        {"profile": "qwen3vl-2b-int4", "files": []},
        {"profile": "qwen3vl-2b-int4", "files": []},
    ]}), encoding="utf-8")

    with pytest.raises(ValueError, match="one profile entry"):
        verify_profile(manifest, root, "qwen3vl-2b-int4")


def test_profile_verifier_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "model"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    link = root / "config.json"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    manifest = _manifest(tmp_path, [{
        "path": "config.json", "bytes": 2,
        "sha256": hashlib.sha256(b"{}").hexdigest(),
    }])

    with pytest.raises(ValueError, match="must not be symlinks"):
        verify_profile(manifest, root, "qwen3vl-2b-int4")


def test_release_lock_rejects_hash_drift(tmp_path: Path) -> None:
    asset = tmp_path / "asset.tar.gz"
    asset.write_bytes(b"unexpected")
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"archive": {
        "filename": asset.name, "bytes": len(b"expected"),
        "sha256": hashlib.sha256(b"expected").hexdigest(),
    }}), encoding="utf-8")
    with pytest.raises(ValueError, match="byte size mismatch"):
        verify_asset(lock, tmp_path, "archive")


def test_qwen_concurrent_launches_get_disjoint_empty_log_sets(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as executor:
        launch_ids = list(executor.map(lambda _: create_launch_logs(tmp_path), range(4)))
    assert len(set(launch_ids)) == 4
    assert all((tmp_path / f"qwen-vllm-{launch_id}.log").read_bytes() == b"" for launch_id in launch_ids)

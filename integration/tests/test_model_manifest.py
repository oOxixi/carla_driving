import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.verify_model_manifest import verify_profile


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

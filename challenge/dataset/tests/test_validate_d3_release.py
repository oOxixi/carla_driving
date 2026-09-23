from __future__ import annotations

import json
from pathlib import Path
import shutil

from challenge.dataset.validate_d3_release import validate_d3_release


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "challenge" / "dataset" / "releases" / "d3_wave1_addon_v1"


def test_detached_signed_d3_release_metadata_gate_passes() -> None:
    report = validate_d3_release(RELEASE, check_images=False)
    assert report["valid"] is True
    assert report["error_count"] == 0
    assert report["splits"]["train"]["samples"] == 1747
    assert report["splits"]["val"]["samples"] == 308
    assert report["splits"]["hard_negative"]["samples"] == 308
    assert report["evidence"]["b1_signature_sha256"]


def test_detached_signature_rejects_changed_release_manifest(tmp_path: Path) -> None:
    copied = tmp_path / "challenge" / "dataset" / "releases" / RELEASE.name
    shutil.copytree(RELEASE, copied, ignore=shutil.ignore_patterns("images"))
    manifest_path = copied / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["counts"]["train_addition"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = validate_d3_release(copied, check_images=False)
    assert report["valid"] is False
    assert any("does not bind release_manifest" in error for error in report["errors"])

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from challenge.dataset.validate_d2_release import validate_release


def _fixture(tmp_path: Path) -> Path:
    release = tmp_path / "challenge" / "dataset" / "releases" / "d2_v1"
    images = release / "images"
    images.mkdir(parents=True)
    manifest_files = {}
    counts = {}
    for name in ("train", "val", "reserved_test_candidates"):
        sample_id = f"sample_{name}"
        image = images / f"{sample_id}.jpg"
        image_bytes = sample_id.encode()
        image.write_bytes(image_bytes)
        rgb_ref = f"challenge/dataset/releases/d2_v1/images/{image.name}"
        row = {
            "sample_id": sample_id,
            "dataset_version": "fixture",
            "metadata": {"group_key": f"group_{name}", "teacher_git_sha": "fixture_sha"},
            "model_request": {"rgb_ref": rgb_ref},
            "quality": {"training_role": "POSITIVE"},
            "visual_input": {
                "rgb_ref": rgb_ref,
                "rgb_sha256": hashlib.sha256(image_bytes).hexdigest(),
                "size_bytes": len(image_bytes),
            },
        }
        path = release / f"{name}.jsonl"
        content = (json.dumps(row) + "\n").encode()
        path.write_bytes(content)
        manifest_files[path.name] = {
            "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)
        }
        report_name = "RESERVED_TEST_CANDIDATE" if name.startswith("reserved") else name.upper()
        counts[report_name] = {"samples": 1}
    (release / "split_report.json").write_text(
        json.dumps({"counts": {"splits": counts}}), encoding="utf-8"
    )
    report_bytes = (release / "split_report.json").read_bytes()
    manifest_files["split_report.json"] = {
        "sha256": hashlib.sha256(report_bytes).hexdigest(), "bytes": len(report_bytes)
    }
    (release / "split_manifest.json").write_text(
        json.dumps({"files": manifest_files}), encoding="utf-8"
    )
    return release


def test_release_gate_accepts_valid_portable_package(tmp_path: Path) -> None:
    report = validate_release(_fixture(tmp_path))
    assert report["valid"] is True
    assert report["referenced_images"] == 3


def test_release_gate_rejects_stale_manifest(tmp_path: Path) -> None:
    release = _fixture(tmp_path)
    manifest_path = release / "split_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["train.jsonl"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = validate_release(release)
    assert report["valid"] is False
    assert any("published train.jsonl differs" in error for error in report["errors"])


def test_release_gate_rejects_split_group_leak(tmp_path: Path) -> None:
    release = _fixture(tmp_path)
    path = release / "val.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["metadata"]["group_key"] = "group_train"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    report = validate_release(release)
    assert report["valid"] is False
    assert "group_key overlap: train/val" in report["errors"]

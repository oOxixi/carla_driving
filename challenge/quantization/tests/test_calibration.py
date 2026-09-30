from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from challenge.quantization.calibration import (
    CalibrationDataset,
    build_development_calibration,
)


def _record(repo: Path, sample_id: str, primary: str = "NORMAL") -> dict:
    image = repo / "images" / f"{sample_id}.jpg"
    image.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.new("RGB", (8, 8), (30, 60, 90)).save(image)
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    request = {
        "source_text": "减速停车",
        "rgb_ref": f"images/{sample_id}.jpg",
        "targets": [],
        "scene_summary": {"traffic_light": "UNKNOWN", "risk_level": "LOW", "min_gap_m": None, "ttc_s": None},
        "constraints": {"speed_limit_mps": 10.0, "max_target_speed_mps": 5.0, "must_stop": True, "allowed_behaviors": ["STOP"]},
        "scene_capabilities": {},
    }
    return {
        "sample_id": sample_id,
        "sample_class": {"primary": primary},
        "metadata": {"scenario_family": "unit"},
        "model_request": request,
        "teacher_plan": {"steps": [{"behavior": "STOP"}]},
        "visual_input": {"rgb_sha256": digest},
    }


def test_build_and_load_development_calibration(tmp_path: Path) -> None:
    rows = [_record(tmp_path, f"s{index}", "SAFETY_CRITICAL" if index == 0 else "NORMAL") for index in range(4)]
    source = tmp_path / "train.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    manifest = build_development_calibration(
        tmp_path, source_jsonl="train.jsonl", output_directory="out", count=3, seed=7,
    )
    assert manifest["formal_release"] is False
    assert manifest["selection"]["selected"] == 3
    dataset = CalibrationDataset.open(tmp_path, "out/calibration.jsonl")
    feed = next(dataset.feeds())
    assert {name: value.shape for name, value in feed.items()} == {
        "rgb": (1, 3, 224, 224), "text_tokens": (1, 32),
        "targets": (1, 8, 14), "state": (1, 64),
    }


def test_protected_source_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "reserved_test.jsonl"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="must not be Test"):
        build_development_calibration(
            tmp_path, source_jsonl=path, output_directory="out", count=1,
        )

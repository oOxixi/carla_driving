from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.run_qwen_vl_decision import load_context


def test_cli_context_loader_uses_frozen_boundary(tmp_path: Path) -> None:
    target = tmp_path / "context.json"
    target.write_text(json.dumps({
        "schema_version": "1.0",
        "request_id": "req-1",
        "frame": 8,
        "sim_time_s": 0.4,
        "voice_command": "慢一点",
        "rgb_ref": "rgb/000008.jpg",
        "scene_state": {"traffic_light": "GREEN"},
        "perception": {"lead_distance_m": 8.0},
        "safety_state": {"risk_level": "MEDIUM"},
    }, ensure_ascii=False), encoding="utf-8")

    context = load_context(target)

    assert context.request_id == "req-1"
    assert context.rgb_ref == "rgb/000008.jpg"
    assert context.perception["lead_distance_m"] == 8.0


def test_cli_context_loader_rejects_non_object_state(tmp_path: Path) -> None:
    target = tmp_path / "bad.json"
    target.write_text(json.dumps({
        "request_id": "req-1",
        "frame": 8,
        "sim_time_s": 0.4,
        "voice_command": "慢一点",
        "scene_state": [],
        "perception": {},
        "safety_state": {},
    }), encoding="utf-8")

    with pytest.raises(TypeError, match="scene_state"):
        load_context(target)

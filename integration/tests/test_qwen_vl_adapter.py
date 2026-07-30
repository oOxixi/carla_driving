from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from integration.qwen_boundary import QwenInputContext
from integration.qwen_vl_adapter import (
    StrictQwenVLAdapter,
    build_strict_qwen_prompt,
    crop_road_roi,
)


class FakeBackend:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[str, Path | None]] = []

    def generate(self, *, prompt: str, image_path: Path | None) -> str:
        self.calls.append((prompt, image_path))
        return self.response  # type: ignore[return-value]


def _context(rgb_ref: str | None = None) -> QwenInputContext:
    return QwenInputContext(
        request_id="req-7",
        frame=7,
        sim_time_s=0.35,
        voice_command="继续走，但前面是红灯",
        rgb_ref=rgb_ref,
        scene_state={"traffic_light": "RED"},
        perception={"visual_valid": True},
        safety_state={"risk_level": "HIGH"},
    )


def test_adapter_resolves_image_and_returns_only_validated_high_level_json(
    tmp_path: Path,
) -> None:
    image = tmp_path / "rgb" / "000007.jpg"
    image.parent.mkdir()
    image.write_bytes(b"not-decoded-by-fake")
    backend = FakeBackend(json.dumps({
        "action": "STOP",
        "confidence": 0.98,
        "requires_confirmation": False,
        "reason_zh": "红灯停车",
        "decision_source": "QWEN_VL",
        "visual_valid": True,
    }))
    adapter = StrictQwenVLAdapter(backend, image_root=tmp_path)

    decision = adapter(_context("rgb/000007.jpg"))

    assert decision["action"] == "STOP"
    assert backend.calls[0][1] == image.resolve()
    assert "禁止字段" in backend.calls[0][0]
    assert adapter.last_trace is not None
    assert adapter.last_trace.request_id == "req-7"
    assert adapter.last_trace.latency_ms >= 0.0


@pytest.mark.parametrize(
    "response",
    [
        "```json\n{\"action\":\"STOP\"}\n```",
        json.dumps({
            "action": "STOP",
            "confidence": 1.0,
            "requires_confirmation": False,
            "brake": 1.0,
        }),
        "",
    ],
)
def test_adapter_rejects_prose_low_level_controls_and_empty_output(
    response: str,
) -> None:
    adapter = StrictQwenVLAdapter(FakeBackend(response))
    with pytest.raises((TypeError, ValueError)):
        adapter(_context())
    assert adapter.last_trace is not None
    assert adapter.last_trace.decision is None
    assert adapter.last_trace.error is not None
    assert adapter.last_trace.raw_output == response


def test_adapter_rejects_image_reference_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.jpg"
    outside.write_bytes(b"x")
    adapter = StrictQwenVLAdapter(FakeBackend("{}"), image_root=tmp_path)

    with pytest.raises(ValueError, match="escapes image_root"):
        adapter(_context("../outside.jpg"))


def test_prompt_serializes_frozen_context_and_never_requests_controls() -> None:
    prompt = build_strict_qwen_prompt(_context())
    assert '"request_id": "req-7"' in prompt
    assert '"traffic_light": "RED"' in prompt
    assert "throttle, brake, steer" in prompt
    assert "action只能是" in prompt
    assert "20km/h=5.56m/s" in prompt
    assert "明确的停车、紧急停车" in prompt
    assert "TTC不大于2秒" in prompt
    assert "绝不能包含target_speed_mps" in prompt
    assert "target_track_id" in prompt
    assert "禁止编造" in prompt
    assert "行人、骑行者、被遮挡目标" in prompt
    assert "无论action是SLOW_DOWN还是STOP都不得漏掉" in prompt


def test_adapter_accepts_only_target_ids_present_in_perception() -> None:
    context = QwenInputContext(
        request_id="target-1",
        frame=1,
        sim_time_s=0.05,
        voice_command="跟随最近的前车",
        rgb_ref=None,
        scene_state={},
        perception={
            "detected_objects": [
                {"track_id": "vehicle_near", "class": "vehicle"},
            ],
        },
        safety_state={},
    )
    valid = StrictQwenVLAdapter(FakeBackend(json.dumps({
        "action": "SLOW_DOWN",
        "target_speed_mps": 3.0,
        "target_track_id": "vehicle_near",
        "confidence": 0.9,
        "requires_confirmation": False,
    })))
    assert valid(context)["target_track_id"] == "vehicle_near"

    fabricated = StrictQwenVLAdapter(FakeBackend(json.dumps({
        "action": "SLOW_DOWN",
        "target_speed_mps": 3.0,
        "target_track_id": "vehicle_missing",
        "confidence": 0.9,
        "requires_confirmation": False,
    })))
    with pytest.raises(ValueError, match="not present"):
        fabricated(context)


def test_adapter_rejects_semantic_target_substitution() -> None:
    context = QwenInputContext(
        request_id="semantic-substitution",
        frame=1,
        sim_time_s=0.1,
        voice_command="减速并跟随正前方的车辆",
        rgb_ref=None,
        scene_state={},
        perception={"detected_objects": [{
            "track_id": "vehicle_far",
            "class": "vehicle",
            "relation": "far_ahead",
        }]},
        safety_state={},
    )
    adapter = StrictQwenVLAdapter(FakeBackend(json.dumps({
        "action": "SLOW_DOWN",
        "confidence": 1.0,
        "requires_confirmation": False,
        "target_track_id": "vehicle_far",
    })))

    with pytest.raises(ValueError, match="explicit voice target is absent"):
        adapter(context)


def test_adapter_accepts_fail_closed_when_explicit_target_absent() -> None:
    context = QwenInputContext(
        request_id="semantic-absent-safe",
        frame=1,
        sim_time_s=0.1,
        voice_command="减速并跟随左侧相邻车道的车辆",
        rgb_ref=None,
        scene_state={},
        perception={"detected_objects": []},
        safety_state={},
    )
    adapter = StrictQwenVLAdapter(FakeBackend(json.dumps({
        "action": "STOP",
        "confidence": 0.4,
        "requires_confirmation": True,
    })))

    assert adapter(context)["action"] == "STOP"


def test_adapter_grounds_approximate_distance_target() -> None:
    context = QwenInputContext(
        request_id="distance-target",
        frame=1,
        sim_time_s=0.1,
        voice_command="减速并跟随距离约26米的前车",
        rgb_ref=None,
        scene_state={},
        perception={"detected_objects": [
            {
                "track_id": "vehicle_26m",
                "class": "vehicle",
                "relation": "far_ahead",
                "distance_m": 26.4,
            },
            {
                "track_id": "vehicle_46m",
                "class": "vehicle",
                "relation": "dense_ahead_3",
                "distance_m": 46.0,
            },
        ]},
        safety_state={},
    )
    adapter = StrictQwenVLAdapter(FakeBackend(json.dumps({
        "action": "SLOW_DOWN",
        "confidence": 1.0,
        "requires_confirmation": False,
        "target_track_id": "vehicle_26m",
    })))

    assert adapter(context)["target_track_id"] == "vehicle_26m"


def test_adapter_corrects_qwen_to_unique_distance_target() -> None:
    context = QwenInputContext(
        request_id="distance-correction",
        frame=1,
        sim_time_s=0.1,
        voice_command="减速并跟随距离约26米的前车",
        rgb_ref=None,
        scene_state={},
        perception={"detected_objects": [
            {
                "track_id": "vehicle_26m",
                "class": "vehicle",
                "relation": "far_ahead",
                "distance_m": 26.4,
            },
            {
                "track_id": "vehicle_46m",
                "class": "vehicle",
                "relation": "dense_ahead_3",
                "distance_m": 46.0,
            },
        ]},
        safety_state={},
    )
    adapter = StrictQwenVLAdapter(FakeBackend(json.dumps({
        "action": "SLOW_DOWN",
        "confidence": 1.0,
        "requires_confirmation": False,
        "target_track_id": "vehicle_46m",
    })))

    assert adapter(context)["target_track_id"] == "vehicle_26m"
    assert adapter.last_trace is not None
    assert adapter.last_trace.target_grounding["status"] == (
        "CORRECTED_UNIQUE"
    )


def test_adapter_ignores_low_confidence_false_positive_for_grounding() -> None:
    context = QwenInputContext(
        request_id="false-positive",
        frame=1,
        sim_time_s=0.1,
        voice_command="减速并跟随正前方的车辆",
        rgb_ref=None,
        scene_state={},
        perception={"detected_objects": [
            {
                "track_id": "vehicle_real",
                "class": "vehicle",
                "relation": "center_ahead",
            },
            {
                "track_id": "vehicle_ghost",
                "class": "vehicle",
                "relation": "center_ahead",
                "confidence": 0.31,
            },
        ]},
        safety_state={},
    )
    adapter = StrictQwenVLAdapter(FakeBackend(json.dumps({
        "action": "SLOW_DOWN",
        "confidence": 1.0,
        "requires_confirmation": False,
        "target_track_id": "vehicle_real",
    })))

    assert adapter(context)["target_track_id"] == "vehicle_real"


def test_road_roi_crop_removes_only_vertical_bands() -> None:
    image = Image.new("RGB", (800, 450), color=(1, 2, 3))

    cropped, metadata = crop_road_roi(
        image,
        top_ratio=0.04,
        bottom_ratio=0.08,
    )

    assert cropped.size == (800, 396)
    assert metadata["original_size"] == [800, 450]
    assert metadata["crop_box_xyxy"] == [0, 18, 800, 414]
    assert metadata["retained_pixel_ratio"] == 0.88


@pytest.mark.parametrize(
    ("top_ratio", "bottom_ratio"),
    [(0.5, 0.0), (0.0, 0.5), (0.4, 0.4)],
)
def test_road_roi_crop_rejects_empty_or_excessive_crop(
    top_ratio: float,
    bottom_ratio: float,
) -> None:
    image = Image.new("RGB", (20, 10))
    with pytest.raises(ValueError):
        crop_road_roi(
            image,
            top_ratio=top_ratio,
            bottom_ratio=bottom_ratio,
        )

"""Dataset boundary for A3 distillation experiments.

Real records remain lossless JSON objects for the future A1 multimodal input
packer.  A deterministic numeric feature encoder exists only to exercise the
D1 training pipeline before the real Student and B1 dataset arrive.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .label_encoder import BEHAVIORS, DistillationLabelEncoder


SAMPLE_WEIGHTS = {
    "normal": 1.0,
    "complex": 1.5,
    "safety_critical": 2.5,
}


class DistillationDataset:
    def __init__(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        label_encoder: DistillationLabelEncoder | None = None,
        sample_weights: Mapping[str, float] | None = None,
    ) -> None:
        self.records = tuple(dict(item) for item in records)
        if not self.records:
            raise ValueError("distillation dataset must not be empty")
        self.label_encoder = label_encoder or DistillationLabelEncoder()
        weights = dict(SAMPLE_WEIGHTS)
        if sample_weights is not None:
            weights.update({str(key): float(value) for key, value in sample_weights.items()})
        if any(not math.isfinite(value) or value <= 0.0 for value in weights.values()):
            raise ValueError("sample weights must be finite and positive")
        self.sample_weights = weights

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        record = self.records[index]
        request = _request(record)
        plan = _plan(record)
        sample_class = _sample_class(record)
        if sample_class not in self.sample_weights:
            raise ValueError(f"unsupported sample_class: {sample_class!r}")
        return {
            "sample_id": str(record.get("sample_id", f"sample-{index:06d}")),
            "request": request,
            "teacher_plan": plan,
            "labels": self.label_encoder.encode(request, plan),
            "sample_class": sample_class,
            "sample_weight": self.sample_weights[sample_class],
            "metadata": dict(record.get("metadata", {})),
        }


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"{source}:{line_number}: invalid JSON: {error}") from error
        if not isinstance(item, dict):
            raise ValueError(f"{source}:{line_number}: record must be an object")
        records.append(item)
    if not records:
        raise ValueError(f"{source}: no records")
    return records


def make_collate_fn(
    *,
    feature_dim: int = 32,
    input_packer: Callable[[Sequence[Mapping[str, Any]]], Mapping[str, Any]] | None = None,
) -> Callable[[Sequence[Mapping[str, Any]]], dict[str, Any]]:
    if feature_dim < 16:
        raise ValueError("feature_dim must be at least 16")

    def collate(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        torch = _torch()
        labels = [item["labels"] for item in samples]
        requests = [item["request"] for item in samples]
        model_inputs = (
            dict(input_packer(requests))
            if input_packer is not None
            else {
                "features": torch.tensor(
                    [_mock_request_features(request, feature_dim) for request in requests],
                    dtype=torch.float32,
                ),
            }
        )
        return {
            "model_inputs": model_inputs,
            "labels": {
                "plan_length": torch.tensor([item["plan_length"] for item in labels], dtype=torch.long),
                "behavior": torch.tensor([item["behavior"] for item in labels], dtype=torch.long),
                "target_pointer": torch.tensor([item["target_pointer"] for item in labels], dtype=torch.long),
                "target_lane": torch.tensor([item["target_lane"] for item in labels], dtype=torch.long),
                "target_speed_mps": torch.tensor(
                    [item["target_speed_mps"] for item in labels], dtype=torch.float32,
                ),
                "completion_type": torch.tensor([item["completion_type"] for item in labels], dtype=torch.long),
                "on_failure": torch.tensor([item["on_failure"] for item in labels], dtype=torch.long),
                "step_mask": torch.tensor([item["step_mask"] for item in labels], dtype=torch.bool),
                "target_speed_mask": torch.tensor(
                    [item["target_speed_mask"] for item in labels], dtype=torch.bool,
                ),
                "confidence": torch.tensor([item["confidence"] for item in labels], dtype=torch.float32),
                "requires_confirmation": torch.tensor(
                    [item["requires_confirmation"] for item in labels], dtype=torch.float32,
                ),
                "replan_conditions": torch.tensor(
                    [item["replan_conditions"] for item in labels], dtype=torch.float32,
                ),
                "sample_weight": torch.tensor(
                    [item["sample_weight"] for item in samples], dtype=torch.float32,
                ),
            },
            "sample_ids": [str(item["sample_id"]) for item in samples],
            "sample_classes": [str(item["sample_class"]) for item in samples],
            "requests": requests,
            "teacher_plans": [item["teacher_plan"] for item in samples],
            "metadata": [item["metadata"] for item in samples],
        }

    return collate


def build_mock_records(count: int = 256) -> list[dict[str, Any]]:
    """Create contract-valid unit-test records, never production training data."""
    if type(count) is not int or count < 2:
        raise ValueError("mock record count must be an integer >= 2")
    patterns = (
        ("KEEP_LANE", "normal"),
        ("SET_SPEED", "normal"),
        ("FOLLOW", "complex"),
        ("AVOID_OBSTACLE", "complex"),
        ("STOP", "safety_critical"),
    )
    records = []
    for index in range(count):
        behavior, sample_class = patterns[index % len(patterns)]
        request_id = f"mock-request-{index:05d}"
        command_id = f"mock-command-{index:05d}"
        targets = [] if behavior in {"KEEP_LANE", "SET_SPEED", "STOP"} else [{
            "target_id": f"vehicle-{index:05d}",
            "class": "vehicle",
            "distance_m": 12.0 + index % 9,
            "relative_speed_mps": -1.0,
            "confidence": 0.95,
            "relation": "center_ahead",
        }]
        request = _mock_request(request_id, command_id, behavior, targets, index)
        plan = _mock_plan(request_id, command_id, behavior, targets, index)
        records.append({
            "sample_id": f"mock-{index:05d}",
            "metadata": {
                "sample_class": sample_class,
                "split": "mock",
                "teacher_git_sha": "MOCK_ONLY",
                "dataset_version": "mock-v1",
            },
            "input": request,
            "teacher": {"maneuver_plan": plan},
            "quality": {"schema_valid": True, "closed_loop_success": True},
        })
    return records


def _request(record: Mapping[str, Any]) -> dict[str, Any]:
    value = record.get("input", record.get("model_request"))
    if not isinstance(value, Mapping):
        raise ValueError("record.input must contain ModelRequest V1")
    return dict(value)


def _plan(record: Mapping[str, Any]) -> dict[str, Any]:
    teacher = record.get("teacher")
    value = teacher.get("maneuver_plan") if isinstance(teacher, Mapping) else None
    if value is None:
        value = record.get("maneuver_plan")
    if not isinstance(value, Mapping):
        raise ValueError("record.teacher.maneuver_plan must contain ManeuverPlan V2")
    return dict(value)


def _sample_class(record: Mapping[str, Any]) -> str:
    metadata = record.get("metadata", {})
    if isinstance(metadata, Mapping) and metadata.get("sample_class"):
        return str(metadata["sample_class"])
    quality = record.get("quality", {})
    if isinstance(quality, Mapping) and quality.get("safety_critical") is True:
        return "safety_critical"
    return "normal"


def _mock_request_features(request: Mapping[str, Any], feature_dim: int) -> list[float]:
    scene = request.get("scene_summary", {})
    targets = request.get("targets", ())
    constraints = request.get("constraints", {})
    text = str(request.get("source_text", ""))
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    features = [0.0] * feature_dim
    features[0] = min(len(text), 1000) / 1000.0
    features[1] = min(len(targets), 12) / 12.0
    features[2] = min(float(scene.get("sim_time_s", 0.0)), 1000.0) / 1000.0
    features[3] = min(float(constraints.get("max_target_speed_mps") or 0.0), 50.0) / 50.0
    features[4] = float(bool(constraints.get("must_stop", False)))
    features[5] = min(float(scene.get("ttc_s") or 20.0), 20.0) / 20.0
    hinted = str(request.get("command_hint", {}).get("intent", "")).upper()
    hinted = "STOP" if hinted == "EMERGENCY_STOP" else hinted
    if hinted in BEHAVIORS and 6 + BEHAVIORS.index(hinted) < feature_dim:
        features[6 + BEHAVIORS.index(hinted)] = 1.0
    digest_start = min(feature_dim, 6 + len(BEHAVIORS))
    for offset, value in enumerate(digest[: feature_dim - digest_start], digest_start):
        features[offset] = value / 255.0
    return features


def _mock_request(
    request_id: str,
    command_id: str,
    behavior: str,
    targets: list[dict[str, Any]],
    index: int,
) -> dict[str, Any]:
    hinted = "EMERGENCY_STOP" if behavior == "STOP" else behavior
    allowed = "AVOID_OBSTACLE" if behavior == "AVOID_OBSTACLE" else behavior
    return {
        "schema_version": "1.0",
        "request_id": request_id,
        "command_id": command_id,
        "created_at_ns": 1_000_000_000 + index,
        "deadline_ns": 2_000_000_000 + index,
        "source_text": f"mock instruction {behavior} {index}",
        "command_hint": {"intent": hinted},
        "rgb_ref": None,
        "routing": {
            "disposition": "QWEN_PLAN",
            "score": 5,
            "reasons": ["MOCK_TRAINING_ONLY"],
            "safe_wait_behavior": "STOP",
        },
        "scene_capabilities": {
            "available_lanes": ["CURRENT", "LEFT_ADJACENT"],
            "left_lane_exists": True,
            "right_lane_exists": False,
            "left_gap_safe": True,
            "right_gap_safe": False,
            "route_available": True,
            "intersection_ahead": False,
            "stop_line_clear": True,
        },
        "scene_summary": {
            "frame_id": index,
            "sim_time_s": index * 0.05,
            "traffic_light": "GREEN",
            "risk_level": "HIGH" if behavior == "STOP" else "LOW",
        },
        "targets": targets,
        "constraints": {
            "speed_limit_mps": 8.0,
            "allowed_behaviors": [allowed],
            "must_stop": behavior == "STOP",
            "max_target_speed_mps": 8.0,
        },
    }


def _mock_plan(
    request_id: str,
    command_id: str,
    behavior: str,
    targets: list[dict[str, Any]],
    index: int,
) -> dict[str, Any]:
    target_id = targets[0]["target_id"] if targets else None
    target_speed = 5.0 if behavior in {"SET_SPEED", "FOLLOW", "AVOID_OBSTACLE"} else None
    completion = {
        "KEEP_LANE": "LANE_CENTERED",
        "SET_SPEED": "SPEED_REACHED",
        "FOLLOW": "TARGET_GAP_REACHED",
        "AVOID_OBSTACLE": "TARGET_PASSED",
        "STOP": "STOPPED",
    }[behavior]
    target_lane = "LEFT_ADJACENT" if behavior == "AVOID_OBSTACLE" else "CURRENT"
    step = {
        "step_id": "step-1",
        "behavior": behavior,
        "target": {
            "target_id": target_id,
            "target_lane": target_lane,
            "target_speed_mps": target_speed,
            "time_gap_s": 2.0 if behavior == "FOLLOW" else None,
            "route_direction": "LEFT" if behavior == "AVOID_OBSTACLE" else None,
        },
        "preconditions": ["PERCEPTION_FRESH"],
        "completion": {
            "type": completion,
            "value": 5.0 if completion in {"SPEED_REACHED", "TARGET_GAP_REACHED"} else None,
            "lane": target_lane if completion == "LANE_CENTERED" else None,
            "hold_frames": 3,
        },
        "timeout_s": 10.0,
        "on_failure": "SAFE_STOP",
    }
    return {
        "schema_version": "2.0",
        "request_id": request_id,
        "command_id": command_id,
        "plan_id": f"mock-plan-{index:05d}",
        "plan_type": "MANEUVER_SEQUENCE",
        "steps": [step],
        "replan_conditions": ["TARGET_LOST"] if target_id else [],
        "confidence": 0.95,
        "requires_confirmation": False,
        "created_at_ns": 1_000_000_100 + index,
        "valid_until_ns": 2_000_000_000 + index,
        "reason_code": "MOCK_TRAINING_ONLY",
        "model_id": "mock-teacher",
    }


def _torch() -> Any:
    try:
        import torch
    except ImportError as error:
        raise RuntimeError(
            "PyTorch is required for distillation batching; install it in the training environment"
        ) from error
    return torch


__all__ = [
    "DistillationDataset", "SAMPLE_WEIGHTS", "build_mock_records",
    "load_jsonl", "make_collate_fn",
]

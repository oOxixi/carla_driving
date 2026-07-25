"""Build schema-v1 multimodal JSONL files from normalized capture records."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "1.0.0"
SPLITS = ("train", "val", "test")
ACTIONS = {
    "START",
    "STOP",
    "SLOW_DOWN",
    "SET_SPEED",
    "EMERGENCY_STOP",
    "TURN_LEFT",
    "TURN_RIGHT",
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
    "AVOID_OBJECT",
    "EMERGENCY_BRAKE",
    "RETURN_TO_LANE",
    "REQUEST_CONFIRMATION",
}
CLASS_MAP = {
    "car": "vehicle",
    "truck": "vehicle",
    "bus": "vehicle",
    "motorcycle": "vehicle",
    "vehicle": "vehicle",
    "person": "pedestrian",
    "pedestrian": "pedestrian",
    "traffic_light": "traffic_light",
    "cone": "cone",
    "barrier": "barrier",
}


def deterministic_split(
    sequence_id: str,
    scenario_id: str,
    seed: int,
    *,
    train_percent: int = 70,
    val_percent: int = 15,
) -> str:
    """Assign an entire sequence/scenario/seed group without frame leakage."""
    if train_percent < 0 or val_percent < 0 or train_percent + val_percent > 100:
        raise ValueError("invalid train/val percentages")
    key = f"{sequence_id}\0{scenario_id}\0{seed}".encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % 100
    if bucket < train_percent:
        return "train"
    if bucket < train_percent + val_percent:
        return "val"
    return "test"


def load_capture_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, start=1):
            if not raw.strip():
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error.msg}") from error
            if not isinstance(payload, dict):
                raise TypeError(f"{path}:{line_number}: capture record must be an object")
            records.append(payload)
    if not records:
        raise ValueError(f"{path}: capture manifest is empty")
    return records


def build_dataset(
    capture_paths: Iterable[Path],
    *,
    dataset_root: Path,
    output_root: Path,
    defaults: Mapping[str, Any],
) -> dict[str, Any]:
    dataset_root = dataset_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    records_by_split: dict[str, list[dict[str, Any]]] = {name: [] for name in SPLITS}
    seen_samples: set[str] = set()
    sequence_splits: dict[str, str] = {}

    for capture_path in capture_paths:
        for payload in load_capture_records(capture_path):
            record = build_record(payload, dataset_root=dataset_root, defaults=defaults)
            sample_id = record["sample_id"]
            if sample_id in seen_samples:
                raise ValueError(f"duplicate generated sample_id {sample_id!r}")
            seen_samples.add(sample_id)
            sequence_id = record["sequence_id"]
            split = record["split"]
            previous = sequence_splits.setdefault(sequence_id, split)
            if previous != split:
                raise ValueError(
                    f"sequence {sequence_id!r} would leak across {previous}/{split}"
                )
            records_by_split[split].append(record)

    records_dir = output_root / "records"
    splits_dir = output_root / "splits"
    records_dir.mkdir(parents=True, exist_ok=True)
    splits_dir.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    for split in SPLITS:
        ordered = sorted(
            records_by_split[split],
            key=lambda item: (item["sequence_id"], item["frame"]["frame_id"]),
        )
        target = records_dir / f"{split}.jsonl"
        target.write_text(
            "".join(
                json.dumps(item, ensure_ascii=False, allow_nan=False, sort_keys=True)
                + "\n"
                for item in ordered
            ),
            encoding="utf-8",
        )
        sequences = sorted({
            str(item["sequence_id"]) for item in ordered
        })
        (splits_dir / f"{split}_sequences.txt").write_text(
            "".join(f"{sequence}\n" for sequence in sequences),
            encoding="utf-8",
        )
        counts[f"{split}_records"] = len(ordered)
        counts[f"{split}_sequences"] = len(sequences)

    report = {
        "schema_version": SCHEMA_VERSION,
        "passed": True,
        "records": sum(counts[f"{split}_records"] for split in SPLITS),
        "sequences": len(sequence_splits),
        "counts": dict(sorted(counts.items())),
        "dataset_root": str(dataset_root),
        "output_root": str(output_root.resolve()),
    }
    evidence_dir = output_root / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def build_record(
    payload: Mapping[str, Any],
    *,
    dataset_root: Path,
    defaults: Mapping[str, Any],
) -> dict[str, Any]:
    frame_id = _integer(payload.get("frame"), "frame", minimum=0)
    sim_time_s = _number(payload.get("sim_time_s"), "sim_time_s", minimum=0.0)
    sequence_id = _text(payload.get("sequence_id", defaults.get("sequence_id")), "sequence_id")
    scenario_id = _text(payload.get("scenario_id", defaults.get("scenario_id")), "scenario_id")
    seed = _integer(payload.get("seed", defaults.get("seed", 0)), "seed")
    split = payload.get("split")
    if split not in SPLITS:
        split = deterministic_split(sequence_id, scenario_id, seed)
    sample_id = str(payload.get("sample_id") or f"{sequence_id}_f{frame_id:06d}")

    rgb = _media_ref(payload.get("rgb_path"), dataset_root)
    lidar = _media_ref(payload.get("lidar_path"), dataset_root)
    audio = _media_ref(payload.get("audio_path"), dataset_root)
    data_level = str(payload.get("data_level", defaults.get("data_level", "closed_loop")))
    if data_level in {"perception", "decision", "closed_loop"} and rgb is None:
        raise ValueError(f"frame {frame_id}: {data_level} requires rgb_path")

    qwen = payload.get("qwen", {})
    if not isinstance(qwen, Mapping):
        raise TypeError(f"frame {frame_id}: qwen must be an object")
    response = qwen.get("response")
    response_map = response if isinstance(response, Mapping) else {}
    decision_action = _action_or_none(response_map.get("action"))
    decision_status = "ok" if decision_action is not None else (
        str(qwen.get("status", "not_run")).lower()
    )
    if decision_status not in {"ok", "timeout", "invalid_output", "unavailable", "not_run"}:
        decision_status = "invalid_output"

    control = payload.get("control", {})
    if not isinstance(control, Mapping):
        raise TypeError(f"frame {frame_id}: control must be an object")
    final_action = _action_or_none(control.get("final_action"))
    expected = payload.get("expected", {})
    if not isinstance(expected, Mapping):
        raise TypeError(f"frame {frame_id}: expected must be an object")
    expected_action = _action_or_none(expected.get("action"))

    vehicle = payload.get("vehicle", {})
    if not isinstance(vehicle, Mapping):
        raise TypeError(f"frame {frame_id}: vehicle must be an object")
    language = payload.get("language", {})
    if not isinstance(language, Mapping):
        raise TypeError(f"frame {frame_id}: language must be an object")
    perception = payload.get("perception", {})
    if not isinstance(perception, Mapping):
        raise TypeError(f"frame {frame_id}: perception must be an object")
    safety = payload.get("safety", {})
    if not isinstance(safety, Mapping):
        raise TypeError(f"frame {frame_id}: safety must be an object")
    environment = payload.get("environment", {})
    if not isinstance(environment, Mapping):
        raise TypeError(f"frame {frame_id}: environment must be an object")
    quality = payload.get("quality", {})
    if not isinstance(quality, Mapping):
        raise TypeError(f"frame {frame_id}: quality must be an object")

    synchronized = bool(payload.get("synchronized", True))
    annotation_status = str(quality.get("annotation_status", "unreviewed"))
    if annotation_status not in {"unreviewed", "single_review", "double_review", "adjudicated"}:
        raise ValueError(f"frame {frame_id}: invalid annotation_status")
    eligible_score = bool(quality.get("eligible_for_score", False))
    if eligible_score and (
        data_level != "closed_loop"
        or not synchronized
        or annotation_status not in {"double_review", "adjudicated"}
    ):
        raise ValueError(
            f"frame {frame_id}: scoring requires closed_loop, synchronized and reviewed"
        )

    transcript = str(language.get("transcript", qwen.get("voice_command", "")))
    normalized_text = str(language.get("normalized_text", transcript))
    decision_actions = [] if decision_action is None else [{"action": decision_action}]
    final_actions = [] if final_action is None else [{"action": final_action}]
    expected_actions = [] if expected_action is None else [{"action": expected_action}]
    return {
        "schema_version": SCHEMA_VERSION,
        "sample_id": sample_id,
        "sequence_id": sequence_id,
        "split": split,
        "data_level": data_level,
        "source": {
            "kind": str(payload.get("source_kind", defaults.get("source_kind", "carla"))),
            "dataset_version": str(defaults.get("dataset_version", "0.9.16")),
            "license": str(defaults.get("license", "CARLA asset terms")),
            "scenario_id": scenario_id,
            "difficulty": str(payload.get("difficulty", defaults.get("difficulty", "unassigned"))),
            "seed": seed,
            "map": str(payload.get("map", defaults.get("map", "Town03"))),
        },
        "frame": {
            "frame_id": frame_id,
            "timestamp_ns": _integer(
                payload.get("timestamp_ns", round(sim_time_s * 1e9)),
                "timestamp_ns",
                minimum=0,
            ),
            "sim_time_s": sim_time_s,
            "synchronized": synchronized,
            "max_sensor_skew_ms": _number(
                payload.get("max_sensor_skew_ms", 0.0),
                "max_sensor_skew_ms",
                minimum=0.0,
            ),
        },
        "sensors": {
            "presence": {
                "rgb_front": rgb is not None,
                "lidar_roof": lidar is not None,
                "audio": audio is not None,
            },
            "rgb_front": rgb,
            "lidar_roof": lidar,
            "audio": audio,
        },
        "language": {
            "command_id": str(language.get("command_id", f"cmd_{frame_id:06d}")),
            "transcript": transcript,
            "normalized_text": normalized_text,
            "asr_confidence": _number(
                language.get("asr_confidence", 1.0),
                "asr_confidence",
                minimum=0.0,
                maximum=1.0,
            ),
            "intent": str(language.get("intent", decision_action or "UNKNOWN")),
            "parameters": dict(language.get("parameters", {})),
            "ambiguity": str(language.get("ambiguity", "none")),
            "target_track_id": language.get("target_track_id"),
        },
        "ego": {
            "speed_kmh": _number(vehicle.get("speed_mps", 0.0), "speed_mps", minimum=0.0) * 3.6,
            "acceleration_mps2": _number(vehicle.get("acceleration_mps2", 0.0), "acceleration_mps2"),
            "lane_id": _lane_id(vehicle.get("lane_id")),
            "route_progress": _number(vehicle.get("route_progress", 0.0), "route_progress", minimum=0.0, maximum=1.0),
            "pose": {
                "x": _number(vehicle.get("x_m", 0.0), "x_m"),
                "y": _number(vehicle.get("y_m", 0.0), "y_m"),
                "yaw_deg": _number(vehicle.get("yaw_deg", 0.0), "yaw_deg"),
            },
        },
        "environment": {
            "weather": str(environment.get("weather", "unknown")),
            "lighting": str(environment.get("lighting", "unknown")),
            "traffic_light_state": str(
                environment.get("traffic_light_state", "unknown")
            ).lower(),
        },
        "perception": {
            "visual_valid": bool(perception.get("visual_valid", rgb is not None)),
            "lidar_valid": bool(perception.get("lidar_valid", lidar is not None)),
            "objects": _objects(perception.get("detected_objects", [])),
        },
        "decision": {
            "provider": str(qwen.get("provider", "qwen")),
            "model": str(qwen.get("model", defaults.get("model", "Qwen2.5-VL"))),
            "model_version": str(qwen.get("model_version", defaults.get("model_version", "local"))),
            "request_id": str(qwen.get("request_id", f"req_{frame_id:06d}")),
            "status": decision_status,
            "requested_actions": decision_actions,
            "confidence": _number(response_map.get("confidence", 0.0), "decision confidence", minimum=0.0, maximum=1.0),
            "requires_confirmation": bool(response_map.get("requires_confirmation", False)),
            "reason": str(response_map.get("reason_zh", "")),
            "raw_output_path": qwen.get("raw_output_path"),
        },
        "safety": {
            "override": bool(safety.get("override", False)),
            "override_reason": safety.get("override_reason"),
            "risk_level": str(safety.get("risk_level", "unknown")).lower(),
            "ttc_s": _optional_number(safety.get("ttc_s"), minimum=0.0),
            "minimum_gap_m": _optional_number(safety.get("minimum_gap_m"), minimum=0.0),
        },
        "control": {
            "final_actions": final_actions,
            "throttle": _number(control.get("throttle", 0.0), "throttle", minimum=0.0, maximum=1.0),
            "brake": _number(control.get("brake", 0.0), "brake", minimum=0.0, maximum=1.0),
            "steer": _number(control.get("steer", 0.0), "steer", minimum=-1.0, maximum=1.0),
        },
        "expected": {
            "actions": expected_actions,
            "target_track_id": expected.get("target_track_id"),
            "task_success": bool(expected.get("task_success", False)),
            "collision": bool(expected.get("collision", False)),
            "red_light_violation": bool(expected.get("red_light_violation", False)),
            "route_completed": bool(expected.get("route_completed", False)),
        },
        "metrics": {
            "latency_ms": {
                name: _optional_number(payload.get("latency_ms", {}).get(name), minimum=0.0)
                for name in ("asr", "perception", "fusion", "decision", "safety", "end_to_end")
            },
        },
        "quality": {
            "annotation_status": annotation_status,
            "eligible_for_training": bool(quality.get("eligible_for_training", False)),
            "eligible_for_score": eligible_score,
            "flags": list(quality.get("flags", [])),
        },
        "provenance": {
            "git_commit": str(defaults.get("git_commit", "unknown")),
            "config_sha256": _sha_text(defaults.get("config_sha256"), "config_sha256"),
            "carla_version": str(defaults.get("carla_version", "0.9.16")),
            "created_at": str(defaults.get("created_at") or datetime.now(timezone.utc).isoformat()),
            "annotation_version": str(defaults.get("annotation_version", "v1.0")),
            "model_artifacts": list(defaults.get("model_artifacts", [])),
        },
    }


def _media_ref(value: object, dataset_root: Path) -> dict[str, Any] | None:
    if value is None:
        return None
    relative = _text(value, "media path").replace("\\", "/")
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or (
        posix.parts and ":" in posix.parts[0]
    ):
        raise ValueError(f"unsafe media path: {relative}")
    path = (dataset_root / Path(*posix.parts)).resolve()
    try:
        path.relative_to(dataset_root)
    except ValueError as error:
        raise ValueError(f"media path escapes dataset root: {relative}") from error
    if not path.is_file():
        raise FileNotFoundError(f"media file not found: {path}")
    suffix = path.suffix.lower().lstrip(".")
    media_format = {"jpg": "jpeg", "jpeg": "jpeg", "wav": "wav-pcm16"}.get(
        suffix, suffix or "binary",
    )
    return {
        "path": relative,
        "sha256": _file_sha256(path),
        "format": media_format,
    }


def _objects(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise TypeError("perception.detected_objects must be an array")
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError("detected object must be an object")
        class_name = CLASS_MAP.get(
            str(item.get("class_name", item.get("class", ""))).lower(),
            "unknown_obstacle",
        )
        obj: dict[str, Any] = {
            "track_id": str(item.get("track_id", f"det_{index:04d}")),
            "class": class_name,
            "confidence": _number(item.get("confidence", 0.0), "object confidence", minimum=0.0, maximum=1.0),
            "distance_m": _optional_number(item.get("distance_m"), minimum=0.0),
            "relative_speed_mps": _optional_number(item.get("relative_speed_mps")),
            "sources": list(item.get("sources", ["annotation"])),
        }
        bbox = item.get("bbox_xyxy_norm")
        if bbox is not None:
            obj["bbox_xyxy_norm"] = list(bbox)
        objects.append(obj)
    return objects


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha_text(value: object, name: str) -> str:
    text = _text(value, name).lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{name} must contain 64 lowercase hexadecimal characters")
    return text


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _integer(value: object, name: str, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _number(
    value: object,
    name: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return result


def _optional_number(
    value: object,
    *,
    minimum: float | None = None,
) -> float | None:
    if value is None:
        return None
    return _number(value, "optional number", minimum=minimum)


def _lane_id(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("lane_id must be integer-compatible or null") from error


def _action_or_none(value: object) -> str | None:
    if value is None:
        return None
    action = str(value).strip().upper()
    if action not in ACTIONS:
        return None
    return action


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_jsonl", nargs="+", type=Path)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--sequence-id", required=True)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--difficulty", choices=("basic", "advanced", "challenge", "unassigned"), default="unassigned")
    parser.add_argument("--map", default="Town03")
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--model", default="Qwen2.5-VL")
    parser.add_argument("--model-version", default="local")
    args = parser.parse_args()
    report = build_dataset(
        args.capture_jsonl,
        dataset_root=args.dataset_root,
        output_root=args.output_root,
        defaults={
            "sequence_id": args.sequence_id,
            "scenario_id": args.scenario_id,
            "seed": args.seed,
            "difficulty": args.difficulty,
            "map": args.map,
            "git_commit": args.git_commit,
            "config_sha256": args.config_sha256,
            "model": args.model,
            "model_version": args.model_version,
        },
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

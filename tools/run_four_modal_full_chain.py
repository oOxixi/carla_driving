"""Evaluate frozen full-chain latency with separate accuracy input contracts."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

from car_control_A.high_level_command import HighLevelCommandAdapter
from car_control_D import SafetySupervisor
from integration.day22.command_adapter import build_high_level_command
from integration.qwen_boundary import QwenInputContext
from integration.qwen_profiles import resolve_qwen_profile
from integration.qwen_remote_backend import OpenAICompatibleQwenVLBackend
from integration.qwen_vl_adapter import StrictQwenVLAdapter
from integration.run_manifest import begin_run, finish_run, update_run_metadata
from tools.four_modal_metrics import (
    evaluate_official_gates,
    evaluate_official_verdict,
    summarize_latency,
)
from tools.run_qwen_batch_benchmark import _evaluate


_STAGE_KEYS = (
    "asr_ms",
    "instruction_parse_ms",
    "asr_nlu_ms",
    "sensor_fusion_ready_ms",
    "qwen_service_ms",
    "post_qwen_control_ms",
    "end_to_end_ms",
)
_REPO_ROOT = Path(__file__).resolve().parents[1]


def audio_to_command(audio: str, t_audio_start_ns: int) -> dict[str, Any]:
    """Load optional ASR dependencies only when a real evaluation is run."""
    from voice_group.pipeline import audio_to_command as run_audio_to_command

    return run_audio_to_command(audio, t_audio_start_ns=t_audio_start_ns)


def preload_voice_models() -> dict[str, Any]:
    """Keep unit tests independent of the optional ASR model package."""
    from voice_group.pipeline import preload_voice_models as preload

    return preload()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_reference(reference: str, *bases: Path) -> Path:
    candidate = Path(reference).expanduser()
    if candidate.is_absolute():
        if candidate.is_file():
            return candidate.resolve()
        raise FileNotFoundError(candidate)
    for base in bases:
        path = (base / candidate).resolve()
        if path.is_file():
            return path
    raise FileNotFoundError(reference)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{path} must contain JSON object rows")
    return rows


def _load_latency_samples(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    samples = payload.get("samples") if isinstance(payload, dict) else None
    if not isinstance(samples, list) or len(samples) != 10:
        raise ValueError("latency manifest must contain exactly ten samples")
    normalized: list[dict[str, Any]] = []
    frame_hashes: set[str] = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("latency manifest samples must be objects")
        audio = _resolve_reference(str(sample["audio_ref"]), path.parent, _REPO_ROOT)
        frame = _resolve_reference(str(sample["frame_ref"]), path.parent, _REPO_ROOT)
        audio_sha256 = str(sample["audio_sha256"])
        frame_sha256 = str(sample["frame_sha256"])
        if _sha256(audio) != audio_sha256 or _sha256(frame) != frame_sha256:
            raise ValueError("latency manifest source hash mismatch")
        if frame_sha256 in frame_hashes:
            raise ValueError("latency manifest frames must have unique content")
        frame_hashes.add(frame_sha256)
        normalized.append({
            **sample,
            "audio_path": audio,
            "frame_path": frame,
        })
    return normalized


def _raw_control(decision: dict[str, Any]) -> dict[str, float]:
    action = decision["action"]
    if action in {"STOP", "EMERGENCY_STOP"}:
        return {"throttle": 0.0, "brake": 1.0, "steer": 0.0}
    if action == "SLOW_DOWN":
        return {"throttle": 0.0, "brake": 0.35, "steer": 0.0}
    return {"throttle": 0.28, "brake": 0.0, "steer": 0.0}


def _context(case: dict[str, Any], transcript: str, index: int) -> QwenInputContext:
    scene_state = dict(case["scene_state"])
    perception = dict(case["perception"])
    safety_state = dict(case["safety_state"])
    required = {"voice", "rgb", "lidar", "ego_state"}
    if set(scene_state.get("modalities", {})) != required:
        raise ValueError("case does not declare all four required modalities")
    lidar = perception.get("lidar_summary", {})
    if not lidar.get("valid") or not lidar.get("raw_sha256"):
        raise ValueError("case has no valid hashed raw LiDAR evidence")
    return QwenInputContext(
        request_id=f"latency-{index:02d}",
        frame=index,
        sim_time_s=index * 0.05,
        voice_command=transcript,
        rgb_ref=case["rgb_ref"],
        scene_state=scene_state,
        perception=perception,
        safety_state=safety_state,
    )


def _safety(
    decision: dict[str, Any] | None,
    transcript: str,
    case: dict[str, Any],
    *,
    watchdog_alerts: tuple[str, ...] = (),
) -> dict[str, Any]:
    supervisor = SafetySupervisor()
    if decision is None:
        raw_control = {"throttle": 0.0, "brake": 0.0, "steer": 0.0}
        command = None
    else:
        high_level = build_high_level_command(
            decision, transcript, command_id=f"full_chain_{case['case_id']}"
        )
        command = HighLevelCommandAdapter().adapt(high_level)
        raw_control = _raw_control(decision)
    scene = case["scene_state"]
    perception = case["perception"]
    lidar = perception.get("lidar_summary", {})
    result = supervisor.arbitrate(
        raw_control,
        {
            "speed_mps": float(scene.get("ego_speed_mps", 0.0)),
            "front_distance_m": lidar.get("front_corridor_min_m"),
            "traffic_light": str(perception.get("traffic_light", "UNKNOWN")).upper(),
            "distance_to_stop_line_m": perception.get("distance_to_stop_line_m"),
            "lane_offset_m": perception.get("lane_offset_m", 0.0),
            "route_deviation_m": perception.get("route_deviation_m", 0.0),
        },
        command,
        {
            "ttc_s": case["safety_state"].get("ttc_s"),
            "emergency_brake_requested": (
                case["safety_state"].get("recommended_action") == "EMERGENCY_STOP"
            ),
        },
        watchdog_alerts=watchdog_alerts,
    )
    return result.to_dict()


def _case_for_frame(
    cases: list[dict[str, Any]], cases_path: Path, frame_path: Path
) -> dict[str, Any]:
    for case in cases:
        try:
            candidate = _resolve_reference(str(case["rgb_ref"]), cases_path.parent)
        except FileNotFoundError:
            continue
        if candidate == frame_path:
            selected = deepcopy(case)
            selected["rgb_ref"] = str(frame_path)
            return selected
    selected = deepcopy(cases[0])
    selected["rgb_ref"] = str(frame_path)
    return selected


def _make_qwen(args: argparse.Namespace) -> tuple[StrictQwenVLAdapter, Any | None, dict[str, object]]:
    profile = resolve_qwen_profile(args.profile)
    if args.qwen_base_url:
        backend = OpenAICompatibleQwenVLBackend(
            base_url=args.qwen_base_url,
            profile=profile,
            api_key=os.environ.get("QWEN_API_KEY", "unused"),
            max_tokens=1,
        )
        return StrictQwenVLAdapter(backend), backend, {
            "profile": profile.name,
            "model": profile.model,
            "model_revision": profile.revision,
            "model_endpoint": args.qwen_base_url,
        }
    assert args.model_path is not None
    return StrictQwenVLAdapter.from_local_checkpoint(args.model_path), None, {
        "profile": profile.name,
        "model": args.model_path.name,
        "model_revision": profile.revision,
        "model_endpoint": None,
    }


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _run_one(
    sample: dict[str, Any],
    case: dict[str, Any],
    qwen: Any,
    index: int,
    phase: str,
) -> dict[str, Any]:
    audio_ready_ns = time.monotonic_ns()
    voice: dict[str, Any] = {}
    transcript = ""
    asr_finished_ns = audio_ready_ns
    nlu_finished_ns = audio_ready_ns
    fusion_ready_ns = audio_ready_ns
    qwen_started_ns = audio_ready_ns
    qwen_finished_ns = audio_ready_ns
    try:
        voice = audio_to_command(
            str(sample["audio_path"]), t_audio_start_ns=audio_ready_ns
        )
        asr_finished_ns = int(voice.get("t_asr_end_ns", time.monotonic_ns()))
        nlu_finished_ns = int(voice.get("t_intent_end_ns", time.monotonic_ns()))
        transcript = str(voice.get("source_text", "")).strip()
        context = _context(case, transcript, index)
        fusion_ready_ns = time.monotonic_ns()
        qwen_started_ns = time.monotonic_ns()
        decision = qwen(context)
        qwen_finished_ns = time.monotonic_ns()
        checks = _evaluate(case, decision)
        final = _safety(decision, transcript, case)
        status, error = "READY", None
    except Exception as exception:
        qwen_finished_ns = time.monotonic_ns()
        decision = None
        checks = {"action": False, "confirmation": False, "target_speed": False, "target_association": False, "all": False}
        final = _safety(None, transcript, case, watchdog_alerts=("QWEN_ERROR",))
        status, error = "ERROR", f"{type(exception).__name__}: {exception}"
    control_ready_ns = time.monotonic_ns()
    stage_timing = {
        "asr_ms": (asr_finished_ns - audio_ready_ns) / 1e6,
        "instruction_parse_ms": (nlu_finished_ns - asr_finished_ns) / 1e6,
        "asr_nlu_ms": (nlu_finished_ns - audio_ready_ns) / 1e6,
        "sensor_fusion_ready_ms": (fusion_ready_ns - nlu_finished_ns) / 1e6,
        "qwen_service_ms": (qwen_finished_ns - qwen_started_ns) / 1e6,
        "post_qwen_control_ms": (control_ready_ns - qwen_finished_ns) / 1e6,
        "end_to_end_ms": (control_ready_ns - audio_ready_ns) / 1e6,
    }
    return {
        "phase": phase,
        "sample_index": index % 10,
        "status": status,
        "error": error,
        "audio_ref": sample["audio_ref"],
        "audio_sha256": sample["audio_sha256"],
        "frame_ref": sample["frame_ref"],
        "frame_sha256": sample["frame_sha256"],
        "expected_intent": sample["expected_intent"],
        "asr_intent": voice.get("intent"),
        "asr_intent_match": voice.get("intent") == sample["expected_intent"],
        "decision": decision,
        "checks": checks,
        "final_safety_control": final,
        "stage_timing": stage_timing,
    }


def _asr_accuracy(manifest_path: Path) -> tuple[dict[str, object], list[dict[str, Any]]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("ASR manifest must be a JSON list")
    records: list[dict[str, Any]] = []
    for sample in payload:
        if not isinstance(sample, dict):
            raise ValueError("ASR manifest entries must be objects")
        try:
            audio_path = _resolve_reference(str(sample["audio"]), manifest_path.parent)
            voice = audio_to_command(str(audio_path), t_audio_start_ns=time.monotonic_ns())
            actual = voice.get("intent")
            records.append({
                "audio": sample["audio"],
                "expected_intent": sample.get("intent"),
                "actual_intent": actual,
                "status": "READY",
                "matches": actual == sample.get("intent"),
            })
        except Exception as exception:
            records.append({
                "audio": sample.get("audio"),
                "expected_intent": sample.get("intent"),
                "actual_intent": None,
                "status": "ERROR",
                "matches": False,
                "error": f"{type(exception).__name__}: {exception}",
            })
    count = len(records)
    return {
        "case_count": count,
        "intent_accuracy": None if count == 0 else sum(record["matches"] for record in records) / count,
        "failed_samples": sum(record["status"] != "READY" for record in records),
    }, records


def _multimodal_accuracy(
    cases: list[dict[str, Any]], cases_path: Path, qwen: Any
) -> tuple[dict[str, object], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for index, source_case in enumerate(cases):
        case = deepcopy(source_case)
        case["rgb_ref"] = str(
            _resolve_reference(str(case["rgb_ref"]), cases_path.parent)
        )
        transcript = str(case["expected_transcript"])
        try:
            decision = qwen(_context(case, transcript, index))
            checks = _evaluate(case, decision)
            records.append({
                "case_id": case["case_id"],
                "status": "READY",
                "checks": checks,
                "decision": decision,
            })
        except Exception as exception:
            records.append({
                "case_id": case.get("case_id", index),
                "status": "ERROR",
                "checks": {"all": False, "action": False, "target_association": False},
                "error": f"{type(exception).__name__}: {exception}",
            })
    count = len(records)
    return {
        "case_count": count,
        "action_target_contract_accuracy": (
            None if count == 0 else sum(record["checks"]["all"] for record in records) / count
        ),
        "failed_samples": sum(record["status"] != "READY" for record in records),
    }, records


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_raw(streams: tuple[Any, Any], record: dict[str, Any]) -> None:
    line = json.dumps(record, ensure_ascii=False) + "\n"
    for stream in streams:
        stream.write(line)
        stream.flush()


def _failed_latency_record(
    sample: dict[str, Any], index: int, phase: str, exception: Exception
) -> dict[str, Any]:
    return {
        "phase": phase,
        "sample_index": index % 10,
        "status": "ERROR",
        "error": f"{type(exception).__name__}: {exception}",
        "audio_ref": sample["audio_ref"],
        "audio_sha256": sample["audio_sha256"],
        "frame_ref": sample["frame_ref"],
        "frame_sha256": sample["frame_sha256"],
        "expected_intent": sample["expected_intent"],
        "asr_intent": None,
        "asr_intent_match": False,
        "decision": None,
        "checks": {"all": False},
        "stage_timing": {key: 0.0 for key in _STAGE_KEYS},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    backend = parser.add_mutually_exclusive_group(required=True)
    backend.add_argument("--model-path", type=Path)
    backend.add_argument("--qwen-base-url")
    parser.add_argument("--profile", default="qwen3vl-2b-int4")
    parser.add_argument("--asr-manifest", type=Path, required=True)
    parser.add_argument("--multimodal-cases", type=Path, required=True)
    parser.add_argument("--latency-manifest", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--measured", type=int, default=10)
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument("--scenario-completion-rate", type=float)
    parser.add_argument("--hardware-label")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    context = begin_run(args.output.parent, {
        "git_commit": _git_commit(),
        "docker_image_digests": os.environ.get("DOCKER_IMAGE_DIGESTS", ""),
        "hardware_label": args.hardware_label or os.environ.get("HARDWARE_LABEL"),
        "profile": args.profile,
        "input_paths": {
            "asr_manifest": str(args.asr_manifest),
            "multimodal_cases": str(args.multimodal_cases),
            "latency_manifest": str(args.latency_manifest),
        },
        "warmup": args.warmup,
        "measured": args.measured,
        "diagnostic": args.diagnostic,
    })
    records: list[dict[str, Any]] = []
    raw_path = context.metrics_dir / "raw_timings.jsonl"
    root_raw_path = args.output.parent / "raw_timings.jsonl"
    remote_backend = None
    try:
        raw_path.touch()
        root_raw_path.touch()
        if args.warmup < 0 or args.measured <= 0:
            raise ValueError("--warmup must be non-negative and --measured positive")
        official_mode = args.warmup == 5 and args.measured == 10
        if not official_mode and not args.diagnostic:
            raise ValueError(
                "official evidence requires --warmup 5 and --measured 10; "
                "pass --diagnostic for any override"
            )
        if args.scenario_completion_rate is not None and not 0.0 <= args.scenario_completion_rate <= 1.0:
            raise ValueError("--scenario-completion-rate must be in [0, 1]")
        latency_manifest = args.latency_manifest.resolve()
        cases_path = args.multimodal_cases.resolve()
        asr_manifest = args.asr_manifest.resolve()
        samples = _load_latency_samples(latency_manifest)
        cases = _load_jsonl(cases_path)
        if not asr_manifest.is_file():
            raise FileNotFoundError(asr_manifest)
        qwen, remote_backend, model_metadata = _make_qwen(args)
        update_run_metadata(context, {
            "dataset_sha256": _sha256(latency_manifest),
            "asr_manifest_sha256": _sha256(asr_manifest),
            "multimodal_cases_sha256": _sha256(cases_path),
            "official_mode": official_mode,
            "validation_status": "PASSED",
            **model_metadata,
        })
        preload_voice_models()
        with raw_path.open("a", encoding="utf-8") as raw_stream, root_raw_path.open(
            "a", encoding="utf-8"
        ) as root_raw_stream:
            for number in range(args.warmup + args.measured):
                sample = samples[number % len(samples)]
                phase = "warmup" if number < args.warmup else "measured"
                try:
                    case = _case_for_frame(cases, cases_path, sample["frame_path"])
                    record = _run_one(sample, case, qwen, number, phase)
                except Exception as exception:
                    record = _failed_latency_record(sample, number, phase, exception)
                records.append(record)
                _append_raw((raw_stream, root_raw_stream), record)
        measured = [record for record in records if record["phase"] == "measured"]
        latency = {
            key: summarize_latency([float(record["stage_timing"][key]) for record in measured])
            for key in _STAGE_KEYS
        }
        gates = evaluate_official_gates(latency)
        parsing_gate = {
            "threshold_ms": 50.0,
            "p95_ms": latency["instruction_parse_ms"]["p95"],
            "passes": latency["instruction_parse_ms"]["p95"] <= 50.0,
        }
        if official_mode and gates["run_accuracy"]:
            asr_accuracy, asr_records = _asr_accuracy(asr_manifest)
            multimodal_accuracy, multimodal_records = _multimodal_accuracy(
                cases, cases_path, qwen
            )
            _write_json(context.metrics_dir / "asr_semantic_accuracy.json", {
                "summary": asr_accuracy, "records": asr_records,
            })
            _write_json(
                context.metrics_dir / "multimodal_contract_accuracy.json",
                {"summary": multimodal_accuracy, "records": multimodal_records},
            )
        else:
            reason = "diagnostic_non_official" if not official_mode else gates["reason"]
            asr_accuracy = {
                "case_count": 0,
                "intent_accuracy": None,
                "status": "NOT_RUN",
                "reason": reason,
            }
            multimodal_accuracy = {
                "case_count": 0,
                "action_target_contract_accuracy": None,
                "status": "NOT_RUN",
                "reason": reason,
            }
        official_verdict = (
            evaluate_official_verdict(
                latency,
                {"asr": asr_accuracy, "multimodal": multimodal_accuracy},
                scenario_completion=args.scenario_completion_rate,
            )
            if official_mode
            else {
                "status": "NOT_OFFICIAL",
                "passes": False,
                "reason": "diagnostic_non_official",
            }
        )
        report = {
            "schema_version": "1.0",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "run_id": context.run_id,
            "raw_timings": str(raw_path),
            "latency": latency,
            "official_gates": gates,
            "instruction_parse_gate": parsing_gate,
            "official_mode": official_mode,
            "official_verdict": official_verdict,
            "accuracy": {
                "asr": asr_accuracy,
                "multimodal": multimodal_accuracy,
            },
            "accuracy_inputs": {
                "asr_manifest": str(asr_manifest),
                "multimodal_cases": str(cases_path),
                "latency_manifest": str(latency_manifest),
            },
            "failed_samples_retained": sum(record["status"] != "READY" for record in records),
            **model_metadata,
        }
        _write_json(args.output, report)
        _write_json(context.metrics_dir / "end_to_end_latency.json", report)
        status = "EARLY_STOP" if gates["status"] == "EARLY_STOP" else "COMPLETED"
        finish_run(context, status, None)
        if gates["status"] == "EARLY_STOP":
            return 2
        return 0 if not official_mode or official_verdict["passes"] else 3
    except Exception as exception:
        finish_run(context, "FAILED", f"{type(exception).__name__}: {exception}")
        raise
    finally:
        if remote_backend is not None:
            remote_backend.close()


if __name__ == "__main__":
    raise SystemExit(main())

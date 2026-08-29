"""Run transcript/audio -> Qwen-VL -> D safety -> final control.

This is an offline full-chain decision/control benchmark. It uses real model
inference and raw CARLA RGB/LiDAR-derived context, but it does not claim that
each record drives a separate CARLA actor. Physical closed-loop evidence stays
in the formal S01/D03/D08 runs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any

from car_control_A.high_level_command import HighLevelCommandAdapter
from car_control_D import SafetySupervisor
from integration.day22.command_adapter import build_high_level_command
from integration.qwen_boundary import QwenInputContext
from integration.qwen_remote_backend import OpenAICompatibleQwenVLBackend
from integration.qwen_vl_adapter import StrictQwenVLAdapter
from tools.four_modal_metrics import summarize_records
from tools.run_qwen_batch_benchmark import _evaluate
from voice_group.pipeline import (
    _text_to_command,
    audio_to_command,
    preload_voice_models,
)


def _raw_control(decision: dict[str, Any]) -> dict[str, float]:
    action = decision["action"]
    if action in {"STOP", "EMERGENCY_STOP"}:
        return {"throttle": 0.0, "brake": 1.0, "steer": 0.0}
    if action == "SLOW_DOWN":
        return {"throttle": 0.0, "brake": 0.35, "steer": 0.0}
    return {"throttle": 0.28, "brake": 0.0, "steer": 0.0}


def _provided_transcript_command(text: str, case_id: str) -> dict[str, Any]:
    """Run the real NLU while explicitly bypassing unavailable audio/ASR."""
    command = _text_to_command(text, f"provided_{case_id}")
    command["confirm_required"] = command.get("status") != "valid"
    return command


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
        request_id=case["case_id"],
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
            decision,
            transcript,
            command_id=f"full_chain_{case['case_id']}",
        )
        command = HighLevelCommandAdapter().adapt(high_level)
        raw_control = _raw_control(decision)
    scene = case["scene_state"]
    perception = case["perception"]
    lidar = perception.get("lidar_summary", {})
    vehicle_state = {
        "speed_mps": float(scene.get("ego_speed_mps", 0.0)),
        "front_distance_m": lidar.get("front_corridor_min_m"),
        "traffic_light": str(
            perception.get("traffic_light", "UNKNOWN")
        ).upper(),
        "distance_to_stop_line_m": perception.get("distance_to_stop_line_m"),
        "lane_offset_m": perception.get("lane_offset_m", 0.0),
        "route_deviation_m": perception.get("route_deviation_m", 0.0),
    }
    risk = {
        "ttc_s": case["safety_state"].get("ttc_s"),
        "emergency_brake_requested": (
            case["safety_state"].get("recommended_action")
            == "EMERGENCY_STOP"
        ),
    }
    result = supervisor.arbitrate(
        raw_control,
        vehicle_state,
        command,
        risk,
        watchdog_alerts=watchdog_alerts,
    )
    return result.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    model_source = parser.add_mutually_exclusive_group(required=True)
    model_source.add_argument("--model-path", type=Path)
    model_source.add_argument(
        "--base-url",
        help="OpenAI-compatible Qwen endpoint, for example http://127.0.0.1:8000/v1",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-VL-7B-Instruct",
        help="Served model name used by --base-url.",
    )
    parser.add_argument("--model-revision")
    parser.add_argument("--timeout-s", type=float, default=8.0)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument(
        "--awq-backend",
        choices=("auto", "torch_awq", "gemm", "gemm_triton"),
        default="auto",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--transcript-source",
        choices=("audio", "provided"),
        default="audio",
        help=(
            "Use real ASR audio (default), or explicitly bypass ASR and use "
            "each case's expected_transcript when audio evidence is unavailable."
        ),
    )
    parser.add_argument(
        "--cases-file",
        type=Path,
        help="Optional JSONL path relative to dataset_dir.",
    )
    parser.add_argument(
        "--category",
        action="append",
        help="Run only selected categories; may be repeated.",
    )
    args = parser.parse_args()
    dataset_dir = args.dataset_dir.resolve()
    cases_file = args.cases_file or Path("cases.jsonl")
    if not cases_file.is_absolute():
        cases_file = dataset_dir / cases_file
    rows = [
        json.loads(line)
        for line in cases_file.read_text(
            encoding="utf-8",
        ).splitlines()
        if line.strip()
    ]
    if args.category:
        requested_categories = set(args.category)
        rows = [
            row for row in rows
            if row.get("category") in requested_categories
        ]
    if args.limit is not None:
        rows = rows[: args.limit]
    if not rows:
        raise ValueError("dataset has no cases")
    if args.transcript_source == "audio" and any(
        not row.get("audio_ref") for row in rows
    ):
        raise ValueError("every full-chain case must have an audio_ref")

    voice_preload = (
        preload_voice_models()
        if args.transcript_source == "audio"
        else {"skipped": True, "reason": "provided_transcript_mode"}
    )
    remote_backend = None
    if args.base_url:
        remote_backend = OpenAICompatibleQwenVLBackend(
            base_url=args.base_url,
            api_key=os.environ.get("QWEN_API_KEY", "unused"),
            model=args.model,
            timeout_s=args.timeout_s,
            max_tokens=1,
            image_max_side=256,
        )
        qwen = StrictQwenVLAdapter(remote_backend, image_root=dataset_dir)
        model_path = None
    else:
        qwen = StrictQwenVLAdapter.from_local_checkpoint(
            args.model_path,
            image_root=dataset_dir,
            max_new_tokens=args.max_new_tokens,
            awq_backend=args.awq_backend,
        )
        model_path = str(args.model_path.resolve())
    records: list[dict[str, Any]] = []
    try:
        for index, case in enumerate(rows):
            started_ns = time.monotonic_ns()
            if args.transcript_source == "audio":
                audio_path = (dataset_dir / case["audio_ref"]).resolve()
                voice = audio_to_command(
                    str(audio_path),
                    t_audio_start_ns=started_ns,
                )
            else:
                provided = str(case["expected_transcript"]).strip()
                voice = _provided_transcript_command(provided, case["case_id"])
            asr_completed_ns = time.monotonic_ns()
            transcript = str(voice.get("source_text", "")).strip()
            qwen_started_ns = time.monotonic_ns()
            try:
                decision = qwen(_context(case, transcript, index))
                qwen_completed_ns = time.monotonic_ns()
                checks = _evaluate(case, decision)
                final = _safety(decision, transcript, case)
                status = "READY"
                error = None
                trace = qwen.last_trace
                visual_preprocess = (
                    None if trace is None else trace.visual_preprocess
                )
                target_grounding = (
                    None if trace is None else trace.target_grounding
                )
                raw_output = None if trace is None else trace.raw_output
            except Exception as exception:
                qwen_completed_ns = time.monotonic_ns()
                decision = None
                checks = {
                    "action": False,
                    "confirmation": False,
                    "target_speed": False,
                    "target_association": False,
                    "all": False,
                }
                final = _safety(
                    None,
                    transcript,
                    case,
                    watchdog_alerts=("QWEN_ERROR",),
                )
                status = "ERROR"
                error = f"{type(exception).__name__}: {exception}"
                visual_preprocess = None
                target_grounding = None
                raw_output = None
            completed_ns = time.monotonic_ns()
            expected_safety = case.get("expected", {}).get("safety_expectation")
            safety_ok = (
                final["safety_override"]
                and final["final_control"]["throttle"] == 0.0
                and final["final_control"]["brake"] > 0.0
                if expected_safety
                else True
            )
            record = {
                "case_id": case["case_id"],
                "category": case["category"],
                "split": case["split"],
                "status": status,
                "audio_ref": case.get("audio_ref"),
                "transcript_source": args.transcript_source,
                "expected_transcript": case["expected_transcript"],
                "asr_transcript": transcript,
                "voice_command": {
                    "intent": voice.get("intent"),
                    "status": voice.get("status"),
                    "confirm_required": voice.get("confirm_required"),
                },
                "decision": decision,
                "expected": case["expected"],
                "checks": {**checks, "safety": safety_ok},
                "final_safety_control": final,
                "latency_ms": {
                    "voice": (asr_completed_ns - started_ns) / 1e6,
                    "qwen": (qwen_completed_ns - qwen_started_ns) / 1e6,
                    "post_qwen_control": (
                        completed_ns - qwen_completed_ns
                    ) / 1e6,
                    "audio_to_final_control": (
                        completed_ns - started_ns
                    ) / 1e6,
                },
                "visual_preprocess": visual_preprocess,
                "target_grounding": target_grounding,
                "raw_qwen_output": raw_output,
                "error": error,
                "modality_evidence": {
                    "audio_sha256": (
                        case.get("audio_sha256")
                        if args.transcript_source == "audio"
                        else None
                    ),
                    "rgb_sha256": case["provenance"]["augmentation"][
                        "output_rgb_sha256"
                    ],
                    "lidar_sha256": case["perception"]["lidar_summary"][
                        "raw_sha256"
                    ],
                    "ego_speed_mps": case["scene_state"]["ego_speed_mps"],
                },
            }
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
    finally:
        if remote_backend is not None:
            remote_backend.close()

    metrics = summarize_records(records)
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model if args.base_url else args.model_path.name,
        "model_revision": args.model_revision,
        "model_path": model_path,
        "model_endpoint": args.base_url,
        "real_model_inference": True,
        "real_asr_inference": args.transcript_source == "audio",
        "transcript_source": args.transcript_source,
        "full_chain_scope": (
            "synthetic TTS audio -> real SenseVoice/NLU"
            if args.transcript_source == "audio"
            else "provided frozen transcript -> real NLU (ASR explicitly bypassed)"
        ) + (
            " -> real RGB and raw-CARLA-LiDAR summary -> real Qwen -> "
            "strict boundary -> deterministic D safety -> final control"
        ),
        "physical_carla_actor_per_case": False,
        "voice_preload": voice_preload,
        **metrics,
        "thresholds": {
            "answerable_joint_accuracy_min": 0.98,
            "answerable_target_association_accuracy_min": 0.98,
            "safety_fault_fail_closed_accuracy_min": 1.0,
            "full_chain_contract_accuracy_min": 0.98,
        },
        "passes_thresholds": False,
        "limitations": ([
            "Audio is synthetic TTS passed through the real ASR model; it is "
            "not official human dialect or 50 dBA evidence."
        ] if args.transcript_source == "audio" else [
            "The source branch does not contain the ten audio files referenced "
            "by cases_v2.jsonl. This run uses the frozen expected transcripts, "
            "so it is not ASR or audio-latency evidence."
        ]) + [
            "Visual stress transforms are labelled augmentations of real CARLA "
            "frames.",
            "Every case reaches final-control arbitration, while physical CARLA "
            "vehicle execution is evidenced separately by formal scenarios.",
        ],
        "records": records,
    }
    acceptance_pairs = (
        (
            report["answerable_joint_accuracy"],
            report["thresholds"]["answerable_joint_accuracy_min"],
        ),
        (
            report["answerable_target_association_accuracy"],
            report["thresholds"][
                "answerable_target_association_accuracy_min"
            ],
        ),
        (
            report["safety_fault_fail_closed_accuracy"],
            report["thresholds"]["safety_fault_fail_closed_accuracy_min"],
        ),
        (
            report["full_chain_contract_accuracy"],
            report["thresholds"]["full_chain_contract_accuracy_min"],
        ),
    )
    report["passes_thresholds"] = all(
        value is not None and value >= threshold
        for value, threshold in acceptance_pairs
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {key: value for key, value in report.items() if key != "records"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report["passes_thresholds"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate a hash-verified evidence index without placeholder claims."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"required evidence is missing: {relative}")
    return {
        "path": relative.replace("\\", "/"),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
    ).strip()


def _count_hashed_entries(value: Any) -> int:
    if isinstance(value, dict):
        current = int(
            isinstance(value.get("path"), str)
            and isinstance(value.get("sha256"), str)
        )
        return current + sum(
            _count_hashed_entries(item) for item in value.values()
        )
    if isinstance(value, list):
        return sum(_count_hashed_entries(item) for item in value)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--four-modal-report",
        default="artifacts/four_modal_0728/full_chain_report_v2.json",
    )
    parser.add_argument(
        "--output",
        default="submission/evidence_index.json",
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    four_modal_path = root / args.four_modal_report
    four_modal = json.loads(four_modal_path.read_text(encoding="utf-8"))
    matrix_path = (
        root / "artifacts/scenario_matrix_0727_final/"
        "scenario_matrix_report.json"
    )
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    stability_path = root / "artifacts/long_stability_0728/report_30min.json"
    stability = json.loads(stability_path.read_text(encoding="utf-8"))

    scenario_files = {
        "S01_set_speed_20": (
            "artifacts/qwen_carla_closed_loop_0727/formal/S01/"
            "S01_set_speed_20_20260727_224749_380324"
        ),
        "D03_front_vehicle_brake": (
            "artifacts/qwen_carla_closed_loop_0727/formal/D03_final/"
            "D03_front_vehicle_brake_20260727_225431_352952"
        ),
        "D08_command_conflict_red_light_continue": (
            "artifacts/qwen_carla_closed_loop_0727/formal/D08/"
            "D08_command_conflict_red_light_continue_20260727_225524_159228"
        ),
    }
    representative_runs = []
    for scenario_id, prefix in scenario_files.items():
        metrics = matrix["per_scenario"][scenario_id]
        representative_runs.append({
            "scenario_id": scenario_id,
            "map": "Town03_Opt",
            "result": (
                "PASS" if metrics["success_rate"] == 1.0 else "FAIL"
            ),
            "matrix_metrics": metrics,
            "summary": _entry(root, f"{prefix}.summary.json"),
            "records": _entry(root, f"{prefix}.jsonl"),
        })

    status_lines = _git(root, "status", "--porcelain").splitlines()
    packaging_paths = {
        args.output.replace("\\", "/"),
        "artifacts/four_modal_0728/source_manifest.json",
    }
    source_status_lines = []
    packaging_status_lines = []
    for line in status_lines:
        changed_path = line[3:].strip().strip('"').replace("\\", "/")
        if changed_path in packaging_paths:
            packaging_status_lines.append(line)
        else:
            source_status_lines.append(line)
    evidence = {
        "schema_version": "2.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "submission": {
            "repository": "https://github.com/oOxixi/carla_driving.git",
            "branch": _git(root, "branch", "--show-current"),
            "base_commit": _git(root, "rev-parse", "HEAD"),
            "working_tree_clean": not status_lines,
            "working_tree_change_count": len(status_lines),
            "source_worktree_clean": not source_status_lines,
            "evidence_packaging_change_count": len(
                packaging_status_lines
            ),
            "carla_version": "0.9.16",
        },
        "real_model_chain": {
            "models_unchanged": {
                "asr": "SenseVoice/FunASR",
                "multimodal": "Qwen2.5-VL-7B-Instruct",
            },
            "real_model_inference": four_modal["real_model_inference"],
            "scope": four_modal["full_chain_scope"],
            "case_count": four_modal["case_count"],
            "metrics": {
                key: four_modal[key]
                for key in (
                    "answerable_joint_accuracy",
                    "asr_exact_accuracy",
                    "voice_command_valid_rate",
                    "answerable_semantic_accuracy",
                    "answerable_target_association_accuracy",
                    "raw_qwen_target_association_accuracy",
                    "grounding_correction_count",
                    "answerable_confirmation_accuracy",
                    "safety_fault_fail_closed_accuracy",
                    "full_chain_contract_accuracy",
                    "latency",
                    "passes_thresholds",
                )
            },
            "report": _entry(root, args.four_modal_report),
            "qwen_model_manifest": _entry(
                root,
                "artifacts/four_modal_0728/"
                "qwen_model_manifest.json",
            ),
            "run_log": _entry(
                root,
                "artifacts/four_modal_0728/full_chain_run_v2.log",
            ),
        },
        "four_modal_dataset": {
            "modalities": ["voice", "RGB", "LiDAR", "ego_state"],
            "manifest": _entry(
                root,
                "artifacts/four_modal_0728/stress_set/cases_v2.jsonl",
            ),
            "audio_report": _entry(
                root,
                "artifacts/four_modal_0728/stress_set/"
                "cases_v2.audio_report.json",
            ),
            "collection_report": _entry(
                root,
                "artifacts/four_modal_0728/collection/"
                "collection_report.json",
            ),
            "stress_report": _entry(
                root,
                "artifacts/four_modal_0728/stress_set/"
                "dataset_report.json",
            ),
            "validation_report": _entry(
                root,
                "artifacts/four_modal_0728/"
                "dataset_validation_v2.json",
            ),
            "limitations": four_modal["limitations"],
        },
        "representative_scenarios": {
            "matrix": _entry(
                root,
                "artifacts/scenario_matrix_0727_final/"
                "scenario_matrix_report.json",
            ),
            "runs": representative_runs,
        },
        "stability": {
            "success": stability["success"],
            "observed_wall_duration_s": stability[
                "observed_wall_duration_s"
            ],
            "aligned_fps": stability["aligned_fps"],
            "dropped_aligned_frames": stability[
                "dropped_aligned_frames"
            ],
            "qwen": {
                key: stability["qwen"][key]
                for key in (
                    "request_count",
                    "ready",
                    "errors",
                    "latency_ms_mean",
                    "latency_ms_p95",
                    "latency_ms_p99",
                    "latency_ms_max",
                )
            },
            "report": _entry(
                root, "artifacts/long_stability_0728/report_30min.json"
            ),
        },
        "validation": {
            "focused_pytest": _entry(
                root, "artifacts/four_modal_0728/pytest.xml"
            ),
            "full_pytest": _entry(
                root, "artifacts/four_modal_0728/pytest_full.xml"
            ),
            "source_manifest": _entry(
                root,
                "artifacts/four_modal_0728/source_manifest.json",
            ),
        },
        "known_submission_gaps": [
            {
                "artifact": "official_human_50_dBA_voice_evidence",
                "status": "MISSING",
                "reason": (
                    "The new full-chain audio is synthetic TTS and is not "
                    "claimed as calibrated 50 dBA evidence."
                ),
            },
            {
                "artifact": "final_demo_video",
                "status": "MISSING",
                "reason": "No final video file is registered in this index.",
            },
            {
                "artifact": "frozen_commit",
                "status": "PENDING" if source_status_lines else "READY",
                "reason": (
                    "base_commit contains the complete source, dataset, "
                    "reports, and task document. Any remaining tracked "
                    "changes are evidence-packaging outputs committed "
                    "immediately after this snapshot."
                ),
            },
        ],
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "registered_file_count": _count_hashed_entries(evidence),
        "known_gap_count": len(evidence["known_submission_gaps"]),
        "working_tree_clean": not status_lines,
        "source_worktree_clean": not source_status_lines,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

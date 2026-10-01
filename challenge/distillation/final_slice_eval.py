"""Read-only development-slice evaluation for an A3 FP32 candidate.

This tool never accepts Test/Frozen paths and never makes a Gate decision.  It
provides the A3-owned TURN/YIELD, plan-length, grounding and speed evidence
required before handing the exact candidate to B2.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader
import yaml

from challenge.dataset.validate_d2_release import canonical_text_sha256

from .a1_student import build_a1_input_packer, build_a1_student
from .dataset import DistillationDataset, load_jsonl, make_collate_fn
from .label_encoder import BEHAVIORS
from .preflight import is_protected_split
from .student_contract import forward_student, validate_student_outputs


LANE_CHANGE_BEHAVIORS = {
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
    "RETURN_TO_LANE",
}
REQUIRED_RECOVERY_BEHAVIORS = ("TURN_LEFT", "YIELD", "PULL_OVER")
REQUIRED_PLAN_LENGTHS = (1, 2, 3, 4)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ratio(correct: int, count: int) -> float | None:
    return correct / count if count else None


def _mae(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def _teacher_steps(record: dict[str, Any]) -> list[dict[str, Any]]:
    teacher = record.get("teacher")
    plan = teacher.get("maneuver_plan") if isinstance(teacher, dict) else None
    if plan is None:
        plan = record.get("teacher_plan", record.get("maneuver_plan"))
    if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list):
        raise ValueError("record does not contain Teacher maneuver-plan steps")
    return plan["steps"]


def audit_dataset_coverage(dataset_cfg: dict[str, Any]) -> dict[str, Any]:
    split_reports: dict[str, Any] = {}
    combined_lengths: dict[int, int] = defaultdict(int)
    combined_behaviors: dict[str, int] = defaultdict(int)
    for split, key in (("train", "train_path"), ("development_validation", "val_path")):
        lengths: dict[int, int] = defaultdict(int)
        behaviors: dict[str, int] = defaultdict(int)
        records = load_jsonl(Path(dataset_cfg[key]))
        for record in records:
            steps = _teacher_steps(record)
            lengths[len(steps)] += 1
            combined_lengths[len(steps)] += 1
            for step in steps:
                name = str(step.get("behavior"))
                behaviors[name] += 1
                combined_behaviors[name] += 1
        split_reports[split] = {
            "sample_count": len(records),
            "plan_length_sample_counts": {
                str(length): lengths[length] for length in REQUIRED_PLAN_LENGTHS
            },
            "required_behavior_step_counts": {
                name: behaviors[name] for name in REQUIRED_RECOVERY_BEHAVIORS
            },
        }
    missing_lengths = [
        length for length in REQUIRED_PLAN_LENGTHS if combined_lengths[length] == 0
    ]
    missing_behaviors = [
        name for name in REQUIRED_RECOVERY_BEHAVIORS if combined_behaviors[name] == 0
    ]
    return {
        "status": (
            "COMPLETE" if not missing_lengths and not missing_behaviors
            else "MISSING_REQUIRED_COVERAGE"
        ),
        "splits": split_reports,
        "combined": {
            "plan_length_sample_counts": {
                str(length): combined_lengths[length] for length in REQUIRED_PLAN_LENGTHS
            },
            "required_behavior_step_counts": {
                name: combined_behaviors[name] for name in REQUIRED_RECOVERY_BEHAVIORS
            },
        },
        "missing_required_plan_lengths": missing_lengths,
        "missing_required_behaviors": missing_behaviors,
    }


@torch.no_grad()
def evaluate_final_slices(
    config_path: Path,
    candidate_dir: Path,
    *,
    batch_size: int | None = None,
) -> dict[str, Any]:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dataset_cfg = cfg["dataset"]
    val_path = Path(dataset_cfg["val_path"])
    if is_protected_split(val_path.name) or "test" in str(val_path).lower():
        raise ValueError("A3 slice evaluation refuses Test/Frozen data")
    manifest_path = candidate_dir / "student_v0_fp32_candidate.json"
    weights_path = candidate_dir / "student_v0_fp32_candidate.pt"
    candidate = json.loads(manifest_path.read_text(encoding="utf-8"))
    if candidate.get("gate_status") != "PENDING_A3_FP32_GATE":
        raise ValueError("slice evaluation requires a candidate pending B2 Gate")
    if candidate.get("source_worktree_dirty") is not False:
        raise ValueError("slice evaluation requires a clean formal candidate")
    if candidate.get("teacher_identity_policy") not in {
        "content_bound_final_cumulative_formal",
        "b1_closeout_cumulative_formal",
    }:
        raise ValueError("candidate is not a governed final cumulative policy")
    if candidate.get("dataset_version") != dataset_cfg["version"]:
        raise ValueError("candidate dataset version does not match the config")
    if candidate.get("config_id") != cfg["model"]["config_id"]:
        raise ValueError("candidate Student config does not match the config")
    if _sha256(weights_path) != candidate.get("weights_sha256"):
        raise ValueError("candidate weights SHA256 mismatch")
    view_path = Path(dataset_cfg["view_manifest_path"])
    if canonical_text_sha256(view_path) != candidate.get("a3_view_manifest_sha256"):
        raise ValueError("candidate view manifest SHA256 mismatch")

    records = load_jsonl(val_path)
    dataset_coverage = audit_dataset_coverage(dataset_cfg)
    dataset = DistillationDataset(
        records,
        asset_root=dataset_cfg["asset_root"],
        require_rgb=True,
        sample_weights=cfg["sampling"]["weights"],
    )
    collate = make_collate_fn(input_packer=build_a1_input_packer())
    loader = DataLoader(
        dataset,
        batch_size=int(batch_size or cfg["training"]["batch_size"]),
        shuffle=False,
        num_workers=0,
        collate_fn=collate,
    )
    model = build_a1_student({"max_steps": 4, "max_targets": 8})
    state = torch.load(weights_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()

    behavior_count: dict[str, int] = defaultdict(int)
    behavior_correct: dict[str, int] = defaultdict(int)
    behavior_speed_errors: dict[str, list[float]] = defaultdict(list)
    plan_length_count: dict[int, int] = defaultdict(int)
    plan_length_correct: dict[int, int] = defaultdict(int)
    plan_sequence_correct: dict[int, int] = defaultdict(int)
    grounding_count = grounding_correct = 0
    distractor_count = distractor_correct = 0
    lane_change_samples = lane_change_behavior_correct = lane_change_plan_correct = 0
    speed_errors: list[float] = []
    speed_error_sample_ids: set[str] = set()

    for batch in loader:
        inputs = {
            name: value.to(device) if torch.is_tensor(value) else value
            for name, value in batch["model_inputs"].items()
        }
        labels = {
            name: value.to(device) if torch.is_tensor(value) else value
            for name, value in batch["labels"].items()
        }
        outputs = forward_student(model, inputs)
        validate_student_outputs(outputs, labels, max_targets=8)
        predicted_behavior = outputs["behavior_logits"].argmax(-1)
        predicted_pointer = outputs["target_pointer_logits"].argmax(-1)
        predicted_length = outputs["plan_length_logits"].argmax(-1) + 1
        predicted_speed = outputs["target_speed_mps"]
        mask = labels["step_mask"].bool()

        for index, sample_id in enumerate(batch["sample_ids"]):
            active = mask[index]
            expected_length = int(labels["plan_length"][index].item()) + 1
            plan_length_count[expected_length] += 1
            plan_length_correct[expected_length] += int(
                int(predicted_length[index].item()) == expected_length
            )
            sequence_ok = bool(
                torch.equal(
                    predicted_behavior[index][active],
                    labels["behavior"][index][active],
                )
            )
            plan_sequence_correct[expected_length] += int(sequence_ok)

            expected_names: list[str] = []
            behavior_ok = True
            for step in active.nonzero().flatten().tolist():
                expected_index = int(labels["behavior"][index, step].item())
                expected_name = BEHAVIORS[expected_index]
                expected_names.append(expected_name)
                correct = int(predicted_behavior[index, step].item()) == expected_index
                behavior_count[expected_name] += 1
                behavior_correct[expected_name] += int(correct)
                behavior_ok = behavior_ok and correct

                expected_pointer = int(labels["target_pointer"][index, step].item())
                if expected_pointer != 8:
                    grounding_count += 1
                    pointer_ok = int(predicted_pointer[index, step].item()) == expected_pointer
                    grounding_correct += int(pointer_ok)
                    if len(batch["requests"][index].get("targets", ())) > 1:
                        distractor_count += 1
                        distractor_correct += int(pointer_ok)

                if bool(labels["target_speed_mask"][index, step].item()):
                    error = abs(
                        float(predicted_speed[index, step].item())
                        - float(labels["target_speed_mps"][index, step].item())
                    )
                    speed_errors.append(error)
                    behavior_speed_errors[expected_name].append(error)
                    if error > 1.0:
                        speed_error_sample_ids.add(str(sample_id))

            if expected_length > 1 and LANE_CHANGE_BEHAVIORS.intersection(expected_names):
                lane_change_samples += 1
                lane_change_behavior_correct += int(behavior_ok)
                lane_change_plan_correct += int(sequence_ok)

    behavior_metrics = {
        name: {
            "step_count": behavior_count[name],
            "accuracy": _ratio(behavior_correct[name], behavior_count[name]),
            "target_speed_count": len(behavior_speed_errors[name]),
            "target_speed_mae_mps": _mae(behavior_speed_errors[name]),
        }
        for name in sorted(behavior_count)
    }
    plan_metrics = {
        str(length): {
            "sample_count": plan_length_count[length],
            "plan_length_accuracy": _ratio(
                plan_length_correct[length], plan_length_count[length]
            ),
            "plan_sequence_accuracy": _ratio(
                plan_sequence_correct[length], plan_length_count[length]
            ),
        }
        for length in sorted(plan_length_count)
    }
    return {
        "schema_version": "1.0",
        "status": "A3_DEVELOPMENT_DIAGNOSTIC_ONLY",
        "gate_status": "PENDING_A3_FP32_GATE",
        "split": "development_validation",
        "candidate": {
            "git_sha": candidate["git_sha"],
            "model_id": candidate["model_id"],
            "config_id": candidate["config_id"],
            "weights_sha256": candidate["weights_sha256"],
            "dataset_version": candidate["dataset_version"],
            "a3_view_manifest_sha256": candidate["a3_view_manifest_sha256"],
        },
        "sample_count": len(dataset),
        "device": str(device),
        "dataset_coverage": dataset_coverage,
        "behavior_slices": behavior_metrics,
        "required_recovery_slices": {
            name: behavior_metrics.get(name)
            for name in REQUIRED_RECOVERY_BEHAVIORS
        },
        "plan_length_slices": plan_metrics,
        "multi_step_lane_change": {
            "definition": "plan_length>1 and expected behavior includes CHANGE_LANE_LEFT/RIGHT or RETURN_TO_LANE",
            "sample_count": lane_change_samples,
            "all_behavior_steps_accuracy": _ratio(
                lane_change_behavior_correct, lane_change_samples
            ),
            "plan_sequence_accuracy": _ratio(lane_change_plan_correct, lane_change_samples),
        },
        "target_grounding": {
            "targeted_step_count": grounding_count,
            "accuracy": _ratio(grounding_correct, grounding_count),
        },
        "target_distractor": {
            "definition": "targeted steps from requests containing more than one candidate target",
            "targeted_step_count": distractor_count,
            "accuracy": _ratio(distractor_correct, distractor_count),
        },
        "target_speed": {
            "step_count": len(speed_errors),
            "mae_mps": _mae(speed_errors),
            "p95_absolute_error_mps": _percentile(speed_errors, 0.95),
            "samples_over_1mps": len(speed_error_sample_ids),
        },
        "limitations": [
            "This report uses A3 development Validation, never B2 Independent/Frozen Test.",
            "It cannot issue A3_FP32_GATE_PASSED.",
            "B2 must evaluate the exact weights SHA independently.",
            "Missing 3/4-step coverage is a dataset gap, not a passing metric.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("challenge/distillation/d3_final_cumulative_formal_config.yaml"),
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path(
            "challenge/distillation/releases/a3_final_fp32_candidate_v1"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int)
    args = parser.parse_args()
    report = evaluate_final_slices(
        args.config, args.candidate_dir, batch_size=args.batch_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

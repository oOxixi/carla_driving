#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if not path.is_file():
        return rows

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(row, dict):
                raise ValueError(
                    f"{path}:{line_no}: row is not a JSON object"
                )

            rows.append(row)

    return rows


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"{path}: expected JSON object"
        )

    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def get_dict(
    sample: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    value = sample.get(key)

    if isinstance(value, dict):
        return value

    return {}


def sample_class(
    sample: dict[str, Any],
) -> str:
    obj = get_dict(
        sample,
        "sample_class",
    )

    return str(
        obj.get(
            "primary",
            "UNKNOWN",
        )
    )


def rejection_counts(
    rows: list[dict[str, Any]],
) -> Counter:
    counter = Counter()

    for row in rows:
        reasons = row.get(
            "rejection_reasons"
        )

        if reasons is None:
            quality = get_dict(
                row,
                "quality",
            )

            reasons = quality.get(
                "rejection_reasons"
            )

        if not isinstance(
            reasons,
            list,
        ):
            continue

        for reason in reasons:
            counter[
                str(reason)
            ] += 1

    return counter


def append_counter(
    lines: list[str],
    counter: Counter,
) -> None:
    if not counter:
        lines.append("- NONE")
        return

    for key, value in sorted(
        counter.items()
    ):
        lines.append(
            f"- {key}: {value}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--raw-valid",
        required=True,
    )

    parser.add_argument(
        "--with-targets",
        required=True,
    )

    parser.add_argument(
        "--with-policy",
        required=True,
    )

    parser.add_argument(
        "--train-eligible",
        required=True,
    )

    parser.add_argument(
        "--hard-cases",
        required=True,
    )

    parser.add_argument(
        "--rejected",
        required=True,
    )

    parser.add_argument(
        "--train",
        required=True,
    )

    parser.add_argument(
        "--val",
        required=True,
    )

    parser.add_argument(
        "--dataset-manifest",
        required=True,
    )

    parser.add_argument(
        "--split-manifest",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    raw_valid_path = Path(
        args.raw_valid
    )

    with_targets_path = Path(
        args.with_targets
    )

    with_policy_path = Path(
        args.with_policy
    )

    train_eligible_path = Path(
        args.train_eligible
    )

    hard_cases_path = Path(
        args.hard_cases
    )

    rejected_path = Path(
        args.rejected
    )

    train_path = Path(
        args.train
    )

    val_path = Path(
        args.val
    )

    dataset_manifest_path = Path(
        args.dataset_manifest
    )

    split_manifest_path = Path(
        args.split_manifest
    )

    output_path = Path(
        args.output
    )

    raw_valid = read_jsonl(
        raw_valid_path
    )

    with_targets = read_jsonl(
        with_targets_path
    )

    with_policy = read_jsonl(
        with_policy_path
    )

    train_eligible = read_jsonl(
        train_eligible_path
    )

    hard_cases = read_jsonl(
        hard_cases_path
    )

    rejected = read_jsonl(
        rejected_path
    )

    train = read_jsonl(
        train_path
    )

    val = read_jsonl(
        val_path
    )

    dataset_manifest = read_json(
        dataset_manifest_path
    )

    split_manifest = read_json(
        split_manifest_path
    )

    if len(raw_valid) != len(with_targets):
        raise SystemExit(
            "raw-valid and with-targets counts differ"
        )

    if len(raw_valid) != len(with_policy):
        raise SystemExit(
            "raw-valid and with-policy counts differ"
        )

    if (
        len(train_eligible)
        + len(hard_cases)
        != len(raw_valid)
    ):
        raise SystemExit(
            "training policy partition does not cover raw dataset"
        )

    if (
        len(train)
        + len(val)
        != len(train_eligible)
    ):
        raise SystemExit(
            "Train + Val does not equal train-eligible dataset"
        )

    total = len(with_policy)

    scenarios = Counter()
    maps = Counter()
    groups = Counter()
    classes = Counter()
    teacher_models = Counter()
    teacher_shas = Counter()

    model_request_v1 = 0
    maneuver_plan_v2 = 0
    rgb_available = 0
    rgb_sha256_present = 0
    target_grounding_valid = 0
    request_command_match = 0

    mapped_target_steps = 0
    no_target_steps = 0
    outside_topk_steps = 0
    invalid_target_steps = 0

    closed_loop_success = 0
    scenario_acceptance_passed = 0
    safety_override_samples = 0
    run_status_inconsistent = 0

    training_policy_classes = Counter()
    hard_case_reasons = Counter()

    for sample in with_policy:
        metadata = get_dict(
            sample,
            "metadata",
        )

        quality = get_dict(
            sample,
            "quality",
        )

        closed_loop = get_dict(
            sample,
            "closed_loop_quality",
        )

        student_targets = get_dict(
            sample,
            "student_targets",
        )

        policy = get_dict(
            sample,
            "training_policy",
        )

        scenarios[
            str(
                metadata.get(
                    "scenario_id"
                )
            )
        ] += 1

        maps[
            str(
                metadata.get(
                    "map"
                )
            )
        ] += 1

        groups[
            str(
                metadata.get(
                    "group_key"
                )
            )
        ] += 1

        classes[
            sample_class(
                sample
            )
        ] += 1

        teacher_models[
            str(
                metadata.get(
                    "teacher_model_id"
                )
            )
        ] += 1

        teacher_shas[
            str(
                metadata.get(
                    "teacher_git_sha"
                )
            )
        ] += 1

        model_request = sample.get(
            "model_request"
        )

        if (
            isinstance(
                model_request,
                dict,
            )
            and model_request.get(
                "schema_version"
            )
            == "1.0"
        ):
            model_request_v1 += 1

        teacher_plan = sample.get(
            "teacher_plan"
        )

        if (
            isinstance(
                teacher_plan,
                dict,
            )
            and teacher_plan.get(
                "schema_version"
            )
            == "2.0"
        ):
            maneuver_plan_v2 += 1

        visual = get_dict(
            sample,
            "visual_input",
        )

        if visual.get(
            "available"
        ) is True:
            rgb_available += 1

        digest = visual.get(
            "rgb_sha256"
        )

        if (
            isinstance(
                digest,
                str,
            )
            and len(
                digest
            )
            == 64
        ):
            rgb_sha256_present += 1

        if (
            quality.get(
                "target_grounding_valid"
            )
            is True
        ):
            target_grounding_valid += 1

        if (
            quality.get(
                "request_id_match"
            )
            is True
            and quality.get(
                "command_id_match"
            )
            is True
        ):
            request_command_match += 1

        steps = student_targets.get(
            "steps"
        )

        if isinstance(
            steps,
            list,
        ):
            for step in steps:
                if not isinstance(
                    step,
                    dict,
                ):
                    continue

                status = step.get(
                    "target_pointer_status"
                )

                if status == "MAPPED":
                    mapped_target_steps += 1

                elif status == "NO_TARGET":
                    no_target_steps += 1

                elif (
                    status
                    == "TARGET_OUTSIDE_TOPK"
                ):
                    outside_topk_steps += 1

                elif (
                    status
                    == "INVALID_TARGET_ID"
                ):
                    invalid_target_steps += 1

        if policy.get(
            "closed_loop_success"
        ) is True:
            closed_loop_success += 1

        if (
            policy.get(
                "scenario_acceptance_passed"
            )
            is True
        ):
            scenario_acceptance_passed += 1

        if (
            policy.get(
                "safety_override_observed"
            )
            is True
        ):
            safety_override_samples += 1

        if (
            policy.get(
                "run_status_inconsistent"
            )
            is True
        ):
            run_status_inconsistent += 1

        policy_class = policy.get(
            "policy_class",
            "UNKNOWN",
        )

        training_policy_classes[
            str(policy_class)
        ] += 1

        reasons = policy.get(
            "quarantine_reasons"
        )

        if isinstance(
            reasons,
            list,
        ):
            for reason in reasons:
                hard_case_reasons[
                    str(reason)
                ] += 1

    train_classes = Counter(
        sample_class(x)
        for x in train
    )

    val_classes = Counter(
        sample_class(x)
        for x in val
    )

    train_groups = {
        get_dict(
            x,
            "metadata",
        ).get(
            "group_key"
        )
        for x in train
    }

    val_groups = {
        get_dict(
            x,
            "metadata",
        ).get(
            "group_key"
        )
        for x in val
    }

    train_ids = {
        x.get(
            "sample_id"
        )
        for x in train
    }

    val_ids = {
        x.get(
            "sample_id"
        )
        for x in val
    }

    group_overlap = (
        train_groups
        & val_groups
    )

    sample_overlap = (
        train_ids
        & val_ids
    )

    lines: list[str] = []

    lines.append(
        "# B1 Teacher Dataset Quality Report"
    )

    lines.append("")

    lines.append(
        "Generated at UTC: "
        + datetime.now(
            timezone.utc
        ).isoformat()
    )

    lines.append("")

    lines.append(
        "Dataset version: "
        + str(
            dataset_manifest.get(
                "dataset_version"
            )
        )
    )

    lines.append("")

    lines.append(
        "## 1. Dataset Overview"
    )

    lines.append("")

    lines.append(
        f"- Raw structurally valid Teacher samples: {len(raw_valid)}"
    )

    lines.append(
        f"- Target-encoded samples: {len(with_targets)}"
    )

    lines.append(
        f"- Policy-labelled samples: {len(with_policy)}"
    )

    lines.append(
        f"- Train-eligible samples: {len(train_eligible)}"
    )

    lines.append(
        f"- Quarantined hard cases: {len(hard_cases)}"
    )

    lines.append(
        f"- Rejected collection records: {len(rejected)}"
    )

    lines.append(
        f"- Unique scenarios: {len(scenarios)}"
    )

    lines.append(
        f"- Unique raw groups: {len(groups)}"
    )

    lines.append("")

    lines.append(
        "## 2. Teacher Provenance"
    )

    lines.append("")

    append_counter(
        lines,
        teacher_models,
    )

    lines.append("")

    lines.append(
        "Teacher Git SHAs:"
    )

    lines.append("")

    append_counter(
        lines,
        teacher_shas,
    )

    lines.append("")

    lines.append(
        "## 3. Structural Integrity"
    )

    lines.append("")

    lines.append(
        f"- Complete ModelRequest V1: {model_request_v1}/{total}"
    )

    lines.append(
        f"- Complete ManeuverPlan V2: {maneuver_plan_v2}/{total}"
    )

    lines.append(
        f"- request_id + command_id alignment: "
        f"{request_command_match}/{total}"
    )

    lines.append(
        f"- Target grounding valid: "
        f"{target_grounding_valid}/{total}"
    )

    lines.append(
        f"- RGB available: {rgb_available}/{total}"
    )

    lines.append(
        f"- RGB SHA256 present: {rgb_sha256_present}/{total}"
    )

    lines.append("")

    lines.append(
        "## 4. Raw Sample Classes"
    )

    lines.append("")

    append_counter(
        lines,
        classes,
    )

    lines.append("")

    lines.append(
        "## 5. Target Pointer Encoding"
    )

    lines.append("")

    lines.append(
        "- Smoke TopK: 8"
    )

    lines.append(
        "- NO_TARGET index: 8"
    )

    lines.append(
        "- Candidate ordering: "
        "`PRESERVE_MODEL_REQUEST_ORDER`"
    )

    lines.append(
        f"- Mapped target steps: {mapped_target_steps}"
    )

    lines.append(
        f"- No-target steps: {no_target_steps}"
    )

    lines.append(
        f"- TARGET_OUTSIDE_TOPK steps: {outside_topk_steps}"
    )

    lines.append(
        f"- Invalid target-id steps: {invalid_target_steps}"
    )

    lines.append("")

    lines.append(
        "TopK=8 is a Smoke-stage validation setting, "
        "not a permanently frozen Student contract."
    )

    lines.append("")

    lines.append(
        "## 6. Training Policy"
    )

    lines.append("")

    lines.append(
        f"- Train eligible: {len(train_eligible)}"
    )

    lines.append(
        f"- Quarantined hard cases: {len(hard_cases)}"
    )

    lines.append(
        f"- Closed-loop command success: {closed_loop_success}/{total}"
    )

    lines.append(
        f"- Scenario acceptance passed: "
        f"{scenario_acceptance_passed}/{total}"
    )

    lines.append(
        f"- Safety override samples retained: "
        f"{safety_override_samples}"
    )

    lines.append(
        f"- Run-status inconsistent but command successful: "
        f"{run_status_inconsistent}"
    )

    lines.append("")

    lines.append(
        "Training policy classes:"
    )

    lines.append("")

    append_counter(
        lines,
        training_policy_classes,
    )

    lines.append("")

    lines.append(
        "Hard-case reasons:"
    )

    lines.append("")

    append_counter(
        lines,
        hard_case_reasons,
    )

    lines.append("")

    lines.append(
        "Policy semantics:"
    )

    lines.append("")

    lines.append(
        "- `teacher_label_valid`: ModelRequest/RGB/ManeuverPlan supervision is structurally valid."
    )

    lines.append(
        "- `closed_loop_success`: supervision command and Teacher plan both terminate successfully."
    )

    lines.append(
        "- `train_eligible`: teacher_label_valid AND closed_loop_success."
    )

    lines.append(
        "- Failed closed-loop Teacher plans remain in raw/hard-case data and are not silently deleted."
    )

    lines.append(
        "- SafetySupervisor override does not automatically invalidate an otherwise successful supervision sample."
    )

    lines.append("")

    lines.append(
        "## 7. Rejected Collection Records"
    )

    lines.append("")

    append_counter(
        lines,
        rejection_counts(
            rejected
        ),
    )

    lines.append("")

    lines.append(
        "Rejected collection records are not part of raw valid Teacher supervision."
    )

    lines.append("")

    lines.append(
        "## 8. Train / Val Split"
    )

    lines.append("")

    lines.append(
        f"- Train samples: {len(train)}"
    )

    lines.append(
        f"- Train groups: {len(train_groups)}"
    )

    lines.append(
        f"- Val samples: {len(val)}"
    )

    lines.append(
        f"- Val groups: {len(val_groups)}"
    )

    lines.append(
        f"- Actual Val ratio over train-eligible data: "
        f"{len(val) / len(train_eligible):.4f}"
    )

    lines.append("")

    lines.append(
        "Train class distribution:"
    )

    lines.append("")

    append_counter(
        lines,
        train_classes,
    )

    lines.append("")

    lines.append(
        "Val class distribution:"
    )

    lines.append("")

    append_counter(
        lines,
        val_classes,
    )

    lines.append("")

    lines.append(
        "## 9. Leakage Validation"
    )

    lines.append("")

    lines.append(
        f"- Group overlap: {len(group_overlap)}"
    )

    lines.append(
        f"- Sample ID overlap: {len(sample_overlap)}"
    )

    lines.append(
        "- Group definition: "
        "`scenario_family + map + route_hash + seed`"
    )

    lines.append(
        "- Adjacent/frame-level random splitting: forbidden"
    )

    lines.append("")

    leakage_pass = (
        len(group_overlap) == 0
        and len(sample_overlap) == 0
    )

    lines.append(
        "**Leakage Validation: "
        + (
            "PASS"
            if leakage_pass
            else "FAIL"
        )
        + "**"
    )

    lines.append("")

    lines.append(
        "## 10. Smoke Split Manifest"
    )

    lines.append("")

    counts = split_manifest.get(
        "counts",
        {},
    )

    lines.append(
        f"- Total split source samples: "
        f"{counts.get('total_samples')}"
    )

    lines.append(
        f"- Total split source groups: "
        f"{counts.get('total_groups')}"
    )

    lines.append(
        f"- Train samples: "
        f"{counts.get('train_samples')}"
    )

    lines.append(
        f"- Val samples: "
        f"{counts.get('val_samples')}"
    )

    lines.append(
        f"- Split seed: "
        f"{split_manifest.get('seed')}"
    )

    lines.append("")

    lines.append(
        "## 11. Artifact Integrity"
    )

    lines.append("")

    artifacts = [
        raw_valid_path,
        with_targets_path,
        with_policy_path,
        train_eligible_path,
        hard_cases_path,
        rejected_path,
        train_path,
        val_path,
        dataset_manifest_path,
        split_manifest_path,
    ]

    for path in artifacts:
        if path.is_file():
            lines.append(
                f"- `{path}`"
            )

            lines.append(
                f"  - SHA256: `{sha256_file(path)}`"
            )

    lines.append("")

    lines.append(
        "## 12. Version Policy"
    )

    lines.append("")

    lines.append(
        "- Current Smoke version: "
        "`teacher_distill_v0.1_smoke`"
    )

    lines.append(
        "- Published dataset versions must not be silently mutated."
    )

    lines.append(
        "- Corrections require a new version or patch version."
    )

    lines.append(
        "- Frozen Test will be created later and must remain immutable after freeze."
    )

    lines.append(
        "- Current Smoke Train/Val are pipeline-validation splits, not final D3 Train/Val/Test."
    )

    lines.append("")

    lines.append(
        "## 13. Smoke Acceptance"
    )

    lines.append("")

    smoke_pass = (
        20 <= len(raw_valid) <= 50
        and len(raw_valid) == len(with_targets)
        and len(raw_valid) == len(with_policy)
        and model_request_v1 == total
        and maneuver_plan_v2 == total
        and rgb_available == total
        and rgb_sha256_present == total
        and request_command_match == total
        and target_grounding_valid == total
        and outside_topk_steps == 0
        and invalid_target_steps == 0
        and len(train_eligible) + len(hard_cases) == total
        and len(train) + len(val) == len(train_eligible)
        and leakage_pass
        and train_classes.get(
            "NORMAL",
            0,
        ) > 0
        and train_classes.get(
            "COMPLEX",
            0,
        ) > 0
        and train_classes.get(
            "SAFETY_CRITICAL",
            0,
        ) > 0
        and val_classes.get(
            "NORMAL",
            0,
        ) > 0
        and val_classes.get(
            "COMPLEX",
            0,
        ) > 0
        and val_classes.get(
            "SAFETY_CRITICAL",
            0,
        ) > 0
    )

    lines.append(
        "**B1 Smoke Dataset Acceptance: "
        + (
            "PASS"
            if smoke_pass
            else "FAIL"
        )
        + "**"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        "\n".join(
            lines
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"QUALITY_REPORT_WRITTEN={output_path}"
    )

    print(
        f"RAW_TEACHER_SAMPLES={len(raw_valid)}"
    )

    print(
        f"TRAIN_ELIGIBLE_SAMPLES={len(train_eligible)}"
    )

    print(
        f"HARD_CASES={len(hard_cases)}"
    )

    print(
        f"SAFETY_OVERRIDE_SAMPLES={safety_override_samples}"
    )

    print(
        f"RUN_STATUS_INCONSISTENT={run_status_inconsistent}"
    )

    print(
        f"TRAIN_SAMPLES={len(train)}"
    )

    print(
        f"VAL_SAMPLES={len(val)}"
    )

    print(
        "QUALITY_REPORT_GENERATION=PASS"
    )


if __name__ == "__main__":
    main()

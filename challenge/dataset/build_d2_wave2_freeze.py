#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json


EXPECTED = {
    "challenge_git_sha": "444d97cea3a76f6b55a6524a52b0302febde223c",
    "teacher_git_sha": "95e97b00def8ec36f12937da34ce8bb9082c4a04",
    "teacher_profile": "b1-pinned-teacher-v4",
    "dataset_version": "teacher_distill_v0.4_d2_expansion_wave2_v4",
    "planned_runs": 2000,
    "valid_samples": 2461,
    "positive_samples": 2320,
    "hard_negative_samples": 141,
    "rejected_samples": 0,
    "unique_sample_ids": 2461,
    "unique_identity_tuples": 2461,
    "unique_group_keys": 2000,
    "formal_plan_sha256":
        "28bccc35cc76483b4d7bcfe4c989238eaabc147b99de399cfbdd439e9467a819",
    "valid_sha256":
        "3d3fdf973865c18e21d341ed5360fb0275f39ca0a3107b7197f3bbcf707db961",
    "rejected_sha256":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "provenance_sha256":
        "3931262733107822e7d6648f4db99d9399c8df36713f5e32a101c9a34d195fec",
    "run_state_sha256":
        "0cd19f5658211762c4f14f8ef60fe2e360602b7d3096d9f223339b11d9f45899",
}

EXPECTED_HN = {
    "CLOSED_LOOP_COLLISION": 65,
    "SAFETY_OVERRIDE_TERMINAL": 25,
    "SCENARIO_ACCEPTANCE_FAILED": 28,
    "TEACHER_EXECUTION_NOT_SUCCEEDED:RUNTIME_ENDED": 4,
    "TEACHER_EXECUTION_NOT_SUCCEEDED:STEP_TIMEOUT": 19,
}

EXPECTED_CLASSES = {
    "COMPLEX": 415,
    "NORMAL": 1917,
    "SAFETY_CRITICAL": 129,
}

FORBIDDEN_ROUTE_REGRESSIONS = (
    "NO_CANONICAL_SUBMIT",
    "ROUTE_UNREACHABLE",
    "distance_contract",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default="artifacts/b1_d2_wave2_2000_teacher_v4",
    )
    parser.add_argument(
        "--plan",
        default=(
            "artifacts/b1_d2_expansion_plan_wave2_v1/"
            "d2_expansion_plan_wave2.json"
        ),
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    plan = Path(args.plan).resolve()

    valid_path = root / "dataset/d2_valid.jsonl"
    rejected_path = root / "dataset/d2_rejected.jsonl"
    prov_path = root / "provenance_manifest.json"
    state_path = root / "run_state.json"
    freeze_path = root / "freeze_manifest.json"

    for p in (plan, valid_path, rejected_path, prov_path, state_path):
        assert p.is_file(), f"missing required file: {p}"

    assert sha256_file(plan) == EXPECTED["formal_plan_sha256"]
    assert sha256_file(valid_path) == EXPECTED["valid_sha256"]
    assert sha256_file(rejected_path) == EXPECTED["rejected_sha256"]
    assert sha256_file(prov_path) == EXPECTED["provenance_sha256"]
    assert sha256_file(state_path) == EXPECTED["run_state_sha256"]

    state = json.loads(state_path.read_text(encoding="utf-8"))
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    valid = read_jsonl(valid_path)
    rejected = read_jsonl(rejected_path)

    runs = state["runs"]
    status_counts = Counter(x.get("status") for x in runs.values())

    assert len(runs) == EXPECTED["planned_runs"]
    assert status_counts == {"SUCCEEDED": EXPECTED["planned_runs"]}

    assert state["dataset_version"] == EXPECTED["dataset_version"]
    assert state["collector_repo_git_sha"] == EXPECTED["challenge_git_sha"]
    assert state["teacher_git_sha"] == EXPECTED["teacher_git_sha"]
    assert state["teacher_profile"] == EXPECTED["teacher_profile"]

    assert (
        prov["collector"]["challenge_repo_git_sha"]
        == EXPECTED["challenge_git_sha"]
    )
    assert (
        prov["teacher"]["teacher_git_sha"]
        == EXPECTED["teacher_git_sha"]
    )

    assert len(valid) == EXPECTED["valid_samples"]
    assert len(rejected) == EXPECTED["rejected_samples"]

    sample_ids = [x["sample_id"] for x in valid]
    assert len(set(sample_ids)) == EXPECTED["unique_sample_ids"]

    identity_tuples = []
    group_keys = []

    roles = Counter()
    sample_classes = Counter()
    hn_reasons = Counter()

    visual_count = 0
    missing_visual = 0
    visual_sha_mismatch = 0
    visual_size_mismatch = 0

    for row in valid:
        meta = row.get("metadata") or {}
        quality = row.get("quality") or {}

        identity_tuples.append((
            meta.get("run_id"),
            meta.get("command_id"),
            meta.get("request_id"),
            meta.get("frame_id"),
        ))
        group_keys.append(meta.get("group_key"))

        role = quality.get("training_role")
        roles[role] += 1

        sample_class = (row.get("sample_class") or {}).get("primary")
        sample_classes[sample_class] += 1

        if role == "HARD_NEGATIVE":
            for reason in quality.get("training_exclusion_reasons") or []:
                hn_reasons[str(reason)] += 1

        visual = row.get("visual_input") or {}
        if visual.get("available") is True:
            visual_count += 1
        else:
            missing_visual += 1

        resolved = visual.get("resolved_path")
        if not resolved:
            missing_visual += 1
            continue

        p = Path(resolved)
        if not p.is_absolute():
            p = Path.cwd() / p

        assert p.is_file(), f"missing visual file: {p}"

        expected_size = visual.get("size_bytes")
        if expected_size is not None and p.stat().st_size != expected_size:
            visual_size_mismatch += 1

        expected_sha = visual.get("rgb_sha256")
        if expected_sha and sha256_file(p) != expected_sha:
            visual_sha_mismatch += 1

    assert len(set(identity_tuples)) == EXPECTED["unique_identity_tuples"]
    assert len(set(group_keys)) == EXPECTED["unique_group_keys"]

    assert roles["POSITIVE"] == EXPECTED["positive_samples"]
    assert roles["HARD_NEGATIVE"] == EXPECTED["hard_negative_samples"]
    assert dict(sorted(hn_reasons.items())) == EXPECTED_HN
    assert dict(sorted(sample_classes.items())) == EXPECTED_CLASSES

    assert visual_count == EXPECTED["valid_samples"]
    assert missing_visual == 0
    assert visual_sha_mismatch == 0
    assert visual_size_mismatch == 0

    logs_root = root / "logs"
    jsonls = sorted(logs_root.rglob("*.jsonl"))
    summaries = sorted(logs_root.rglob("*.summary.json"))

    jsonl_dirs = {p.parent for p in jsonls}
    summary_dirs = {p.parent for p in summaries}

    assert len(jsonls) == 2000
    assert len(summaries) == 2000
    assert jsonl_dirs == summary_dirs

    route_regression = {
        "NO_CANONICAL_SUBMIT": 0,
        "ROUTE_UNREACHABLE": 0,
        "distance_contract": 0,
    }

    # Fast raw-text regression scan.
    for p in jsonls:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                for term in FORBIDDEN_ROUTE_REGRESSIONS:
                    if term in line:
                        route_regression[term] += line.count(term)

    assert route_regression == {
        "NO_CANONICAL_SUBMIT": 0,
        "ROUTE_UNREACHABLE": 0,
        "distance_contract": 0,
    }

    manifest = {
        "freeze_name": "b1_d2_wave2_teacher_v4",
        "freeze_status": "PASS",
        "challenge_git_sha": EXPECTED["challenge_git_sha"],
        "teacher_git_sha": EXPECTED["teacher_git_sha"],
        "teacher_profile": EXPECTED["teacher_profile"],
        "dataset_version": EXPECTED["dataset_version"],
        "planned_runs": 2000,
        "executed_runs": 2000,
        "runner_success_count": 2000,
        "runner_failed_count": 0,
        "valid_samples": 2461,
        "rejected_samples": 0,
        "positive_samples": 2320,
        "hard_negative_samples": 141,
        "hard_negative_reason_counts": EXPECTED_HN,
        "sample_class_counts": EXPECTED_CLASSES,
        "unique_sample_ids": 2461,
        "unique_identity_tuples": 2461,
        "unique_group_keys": 2000,
        "visual_input_count": 2461,
        "missing_visual_inputs": 0,
        "visual_sha256_mismatch": 0,
        "visual_size_mismatch": 0,
        "log_jsonl_count": 2000,
        "log_summary_count": 2000,
        "log_pair_count": 2000,
        "route_regression": route_regression,
        "sha256": {
            "formal_plan": EXPECTED["formal_plan_sha256"],
            "d2_valid_jsonl": EXPECTED["valid_sha256"],
            "d2_rejected_jsonl": EXPECTED["rejected_sha256"],
            "provenance_manifest": EXPECTED["provenance_sha256"],
            "run_state": EXPECTED["run_state_sha256"],
        },
    }

    freeze_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print("FREEZE_MANIFEST =", freeze_path)
    print("FREEZE_MANIFEST_SHA256 =", sha256_file(freeze_path))
    print("VALID_SAMPLES = 2461")
    print("POSITIVE_SAMPLES = 2320")
    print("HARD_NEGATIVE_SAMPLES = 141")
    print("REJECTED_SAMPLES = 0")
    print("UNIQUE_GROUP_KEYS = 2000")
    print("ROUTE_REGRESSION = PASS")
    print("VISUAL_INTEGRITY = PASS")
    print("D2_WAVE2_ACQUISITION_FREEZE=PASS")


if __name__ == "__main__":
    main()

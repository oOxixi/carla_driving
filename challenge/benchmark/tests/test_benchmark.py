import json
from pathlib import Path

from challenge.benchmark.benchmark import (
    canonical_lf_sha256,
    load_benchmark_cases,
)


ROOT = Path(__file__).resolve().parents[3]
RELEASE_DIR = ROOT / "challenge" / "dataset" / "releases" / "d2_v1_1"
VAL_PATH = RELEASE_DIR / "val.jsonl"
MANIFEST_PATH = RELEASE_DIR / "release_manifest.json"


def test_signed_val_matches_b1_release_manifest() -> None:
    """B2 must evaluate exactly the B1-signed Validation artifact."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    signed_val = manifest["files"]["val.jsonl"]

    cases = load_benchmark_cases(VAL_PATH)

    assert len(cases) == signed_val["rows"] == 539
    assert canonical_lf_sha256(VAL_PATH) == signed_val["sha256"]


def test_benchmark_case_identity_is_traceable() -> None:
    """Every case must keep a unique ID and matching request/plan identity."""
    cases = load_benchmark_cases(VAL_PATH)

    sample_ids = [case["sample_id"] for case in cases]

    assert len(sample_ids) == len(set(sample_ids))

    for case in cases:
        request = case["model_request"]
        plan = case["teacher_plan"]

        assert request["request_id"] == plan["request_id"]
        assert request["command_id"] == plan["command_id"]
        assert plan["schema_version"] == "2.0"
        assert plan["steps"]


def test_canonical_hash_is_stable_across_line_endings(
    tmp_path: Path,
) -> None:
    """Windows CRLF checkout and repository LF bytes must hash identically."""
    lf_path = tmp_path / "lf.jsonl"
    crlf_path = tmp_path / "crlf.jsonl"

    lf_path.write_bytes(b'{"sample": 1}\n{"sample": 2}\n')
    crlf_path.write_bytes(b'{"sample": 1}\r\n{"sample": 2}\r\n')

    assert canonical_lf_sha256(lf_path) == canonical_lf_sha256(crlf_path)

def test_benchmark_config_matches_a3_gate_contract() -> None:
    """B2 policy must stay aligned with the A3 FP32 promotion contract."""
    import yaml

    from challenge.distillation.artifacts import (
        CORE_METRICS,
        FORMAL_GATE_TEACHER_V4,
        SAFETY_METRICS,
    )

    config_path = (
        ROOT / "challenge" / "benchmark" / "benchmark_config.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["purpose"] == "A3_FP32_GATE"

    dataset = config["dataset"]
    assert dataset["split"] == "validation"
    assert dataset["independence_required"] is True
    assert dataset["development_val_allowed"] is False
    assert dataset["frozen_test_allowed"] is False

    # Until B1 provides/finalizes the independent Validation package,
    # B2 must fail closed rather than silently use Development Val.
    assert config["status"] == "WAITING_FOR_INDEPENDENT_VALIDATION"
    assert dataset["case_manifest_path"] is None

    assert tuple(config["metrics"]["core"]) == CORE_METRICS
    assert tuple(config["metrics"]["safety"]) == SAFETY_METRICS

    assert config["gate"]["schema_validity_required"] == 1.0
    assert config["gate"]["max_core_drop"] == 0.015
    assert config["gate"]["max_safety_drop"] == 0.0

    teacher = config["teacher"]

    for field, expected in FORMAL_GATE_TEACHER_V4.items():
        assert teacher[field] == expected
    metric_policy = config["gate_metric_policy"]

    assert metric_policy["metric_implementation"] == (
        "challenge.distillation.metrics.compute_batch_metrics"
    )
    assert metric_policy["denominator_implementation"] == (
        "challenge.distillation.metrics.metric_denominators"
    )
    assert metric_policy["aggregation"] == "micro"
    assert metric_policy["denominator_source"] == (
        "frozen_reference_labels"
    )
    assert metric_policy["empty_denominator"] == "null"

    failure_handling = metric_policy["failure_handling"]

    assert failure_handling["statuses"] == [
        "INFERENCE_ERROR",
        "INVALID_OUTPUT",
    ]
    assert failure_handling["numerator_credit"] == 0
    assert failure_handling["denominator"] == (
        "include_reference_eligible_opportunities"
    )

    assert metric_policy["success_only_filter_allowed"] is False
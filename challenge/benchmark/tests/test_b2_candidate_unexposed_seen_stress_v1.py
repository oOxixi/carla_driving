from __future__ import annotations

from pathlib import Path

from tools.prepare_b2_proxy_unseen_v1 import _read_json, _verify_candidate
from tools.run_b2_candidate_unexposed_seen_stress_v1 import (
    audit_exposure,
    load_frozen_policy,
    verify_source_release,
)


ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = (
    ROOT
    / "challenge"
    / "benchmark"
    / "b2_proxy_unseen_v1"
    / "candidate_unexposed_seen_stress_policy.json"
)
DESIGN_PATH = POLICY_PATH.with_name("acquisition_design.json")


def test_stress_policy_is_canonical_frozen_and_matches_candidate() -> None:
    policy, digest = load_frozen_policy(POLICY_PATH)
    design = _read_json(DESIGN_PATH)
    candidate = _verify_candidate(ROOT, design)

    assert len(digest) == 64
    assert policy["policy_status"] == "FROZEN_PRE_INFERENCE"
    assert policy["formal_gate_eligible"] is False
    assert policy["candidate"]["weights_sha256"] == candidate["weights_sha256"]
    assert policy["candidate"]["fp32_onnx_sha256"] == candidate["onnx_sha256"]
    assert policy["candidate"]["adapter_sha256"] == candidate["adapter_sha256"]


def test_locked_308_case_source_preflight_and_exposure_boundary() -> None:
    policy, _ = load_frozen_policy(POLICY_PATH)
    cases, source = verify_source_release(ROOT, policy)
    exposure = audit_exposure(ROOT, cases, policy)

    assert source["sample_count"] == 308
    assert source["primary_counts"] == {
        "complex": 56,
        "normal": 199,
        "safety_critical": 53,
    }
    assert source["all_model_requests_and_teacher_plans_schema_valid"] is True
    assert source["rgb"]["all_sha256_and_size_verified"] is True
    assert exposure["classification"] == "CANDIDATE_UNEXPOSED_SEEN_STRESS"
    assert exposure["required_zero_overlap_pass"] is True
    assert all(
        exposure["overlap_counts"][name] == 0
        for name in ("sample_id", "group_key", "rgb_sha256", "seed")
    )
    assert exposure["overlap_counts"]["scenario_id"] == 16
    assert exposure["overlap_counts"]["source_text_sha256"] == 15

"""The three-way claim scope must stay fail-closed (unified plan 2026-09-30)."""

from challenge.hil.claim_scope import (
    SCOPE_BPU_ESTIMATED,
    SCOPE_J6P_MEASURED,
    SCOPE_X86_MEASURED,
    classify_source,
    validate_claims,
)


def test_source_labels_map_to_the_three_classes():
    assert classify_source("x86_inprocess") == SCOPE_X86_MEASURED
    assert classify_source("x86_soak") == SCOPE_X86_MEASURED
    assert classify_source("bpu_estimate") == SCOPE_BPU_ESTIMATED
    assert classify_source("horizon_toolchain") == SCOPE_BPU_ESTIMATED
    assert classify_source("j6p_board") == SCOPE_J6P_MEASURED
    assert classify_source("cloud_board") == SCOPE_J6P_MEASURED
    assert classify_source("something_unknown") is None
    assert classify_source(None) is None


def test_x86_measurement_needs_a_raw_artefact():
    report = validate_claims([
        {"name": "planner_e2e_p50", "scope": SCOPE_X86_MEASURED, "raw_artifacts": ["latency_raw.csv"]},
        {"name": "peak_rss", "scope": SCOPE_X86_MEASURED},
    ])
    assert report["status"] == "FAIL"
    assert any("without a raw artefact" in error for error in report["errors"])
    assert report["claims"][0]["errors"] == []


def test_an_estimate_may_not_be_published_as_a_board_measurement():
    report = validate_claims([{
        "name": "bpu_latency", "scope": SCOPE_J6P_MEASURED, "estimated": True,
        "device": "j6p-01", "raw_log": "board.log",
    }])
    assert report["status"] == "FAIL"
    assert any("estimated=true" in error for error in report["errors"])


def test_board_claim_needs_device_identity_and_a_raw_log():
    report = validate_claims([{"name": "j6p_latency", "scope": SCOPE_J6P_MEASURED, "device": "j6p-01"}])
    assert report["status"] == "FAIL"
    assert any("missing ['raw_log']" in error for error in report["errors"])


def test_estimate_needs_tool_version_method_and_model_digest():
    report = validate_claims([{
        "name": "bpu_estimated_latency", "scope": SCOPE_BPU_ESTIMATED,
        "tool": "hbdk", "method": "compile latency analysis",
    }])
    assert report["status"] == "FAIL"
    assert any("tool_version" in error and "model_sha256" in error for error in report["errors"])


def test_unknown_source_is_rejected_rather_than_guessed():
    report = validate_claims([{"name": "mystery", "source": "colleague_said_so"}])
    assert report["status"] == "FAIL"
    assert any("unknown scope" in error for error in report["errors"])


def test_a_fully_evidenced_table_passes_and_counts_by_class():
    report = validate_claims([
        {"name": "planner_e2e_p50", "scope": SCOPE_X86_MEASURED, "raw_artifacts": ["latency_raw.csv"]},
        {"name": "bpu_estimated_latency", "scope": SCOPE_BPU_ESTIMATED, "tool": "hbdk",
         "tool_version": "4.11.11", "method": "hb_compile latency analysis", "model_sha256": "ab" * 32},
        {"name": "j6p_latency", "scope": SCOPE_J6P_MEASURED, "device": "j6p-01", "raw_log": "board.log"},
    ])
    assert report["status"] == "PASS"
    assert report["summary"] == {SCOPE_X86_MEASURED: 1, SCOPE_BPU_ESTIMATED: 1, SCOPE_J6P_MEASURED: 1}
    assert "X86 measured != BPU estimated != J6P measured" in report["policy_note"]

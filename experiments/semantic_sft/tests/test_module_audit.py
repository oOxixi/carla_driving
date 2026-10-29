import copy

import pytest

from experiments.semantic_sft.data import audit_rows
from experiments.semantic_sft.environment import compare_module_layout, inventory
from experiments.semantic_sft.tests.test_review import reviewed


def modules():
    prefix = "model.language_model.layers.3.self_attn."
    return [{"name": prefix + name, "module_type": "torch.nn.modules.linear.Linear",
             "in_features": 2048, "out_features": outgoing, "weight_shape": [outgoing, 2048],
             "weight_device": "meta"} for name, outgoing in [("q_proj", 4096), ("v_proj", 512)]]


def test_meta_layout_matches_index_and_only_estimates_adapter_parameters():
    rows = modules()
    before = copy.deepcopy(rows)
    report = compare_module_layout(rows, [r["name"] for r in rows], rank=8)
    assert report["status"] == "PASS" and report["module_count"] == 2
    assert report["candidate_lora_parameters_estimate"] == 69632
    assert report["candidate_adapter_fp32_bytes_estimate"] == 278528
    assert not report["peft_injection_verified"] and not report["ready_for_training"]
    assert rows == before


@pytest.mark.parametrize("field,value,error", [
    ("name", "model.visual.blocks.0.q_proj", "TARGET_OUTSIDE_ALLOWED_LANGUAGE_QV"),
    ("name", "mtp.layers.3.self_attn.q_proj", "TARGET_OUTSIDE_ALLOWED_LANGUAGE_QV"),
    ("weight_device", "cuda", "NON_META_TARGET"),
    ("module_type", "torch.nn.modules.conv.Conv2d", "TARGET_NOT_LINEAR"),
    ("weight_shape", [2048, 4096], "LINEAR_SHAPE_MISMATCH"),
])
def test_unsafe_targets_are_not_certified(field, value, error):
    rows = modules()
    rows[0][field] = value
    report = compare_module_layout(rows, [r["name"] for r in rows], rank=8)
    assert report["status"] == "FAIL"
    assert any(e.startswith(error) for e in report["errors"])


def test_missing_extra_duplicate_targets_and_invalid_rank_are_rejected():
    assert compare_module_layout([], [], rank=8)["status"] == "FAIL"
    rows = modules()
    assert compare_module_layout(rows, [], rank=8)["status"] == "FAIL"
    assert compare_module_layout([rows[0], rows[0]], [rows[0]["name"]], rank=8)["status"] == "FAIL"
    with pytest.raises(ValueError):
        compare_module_layout(rows, [r["name"] for r in rows], rank=0)
    with pytest.raises(ValueError, match="local model path"):
        inventory(module_audit=True)


def test_first_reviewed_coverage_excludes_quarantine_and_does_not_invent_split():
    rows, _ = reviewed()
    report = audit_rows(rows)
    coverage = report["split_coverage_diagnostics"]
    assert coverage["groups_by_family"]["negative_instruction"] == ["no_left_slow_park_02"]
    assert coverage["families_needing_more_groups"] == ["negative_instruction"]
    assert sum(len(groups) for groups in coverage["groups_by_family"].values()) == 11
    assert all(r["split"] == "UNASSIGNED" for r in rows)
    assert not report["data_ready_for_tokenization"]
    rejected = copy.deepcopy(rows)
    rejected[14]["annotation_status"] = rejected[15]["annotation_status"] = "REJECTED"
    assert audit_rows(rejected)["split_coverage_diagnostics"]["groups_by_family"]["negative_instruction"] == []
    rows[14]["reviews"][0]["label_sha256"] = "0" * 64
    rows[15]["reviews"][0]["label_sha256"] = "0" * 64
    assert audit_rows(rows)["split_coverage_diagnostics"]["groups_by_family"]["negative_instruction"] == []


def test_module_flag_cannot_run_under_other_modes_or_without_model_path(tmp_path, monkeypatch):
    from experiments.semantic_sft import prepare
    output = tmp_path / "not_created"
    for mode in ["review", "environment"]:
        monkeypatch.setattr("sys.argv", ["prepare", mode, "--module-audit", "--output-dir", str(output)])
        with pytest.raises(SystemExit):
            prepare.main()
    assert not output.exists()

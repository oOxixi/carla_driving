"""Small regressions for the invalid legacy Teacher denominator."""
import json
from pathlib import Path
import pytest
from challenge.export.compute_flops import analyze_model


def test_student_report_does_not_certify_legacy_teacher_ratio():
    report=analyze_model()
    assert report["flops_per_fixed_batch"] == 498640896
    assert report["ratio_pass"] is None
    assert report["teacher_flops_lower_bound_one_text_token"] is None


def test_teacher_mlp_bound_uses_pinned_configuration():
    from challenge.export.teacher_flops import mlp_lower_bound
    root=Path(__file__).resolve().parents[1]
    config=json.loads((root/"export/teacher_config_pinned.json").read_text(encoding="utf-8"))
    assert mlp_lower_bound(config)==1811939328
    changed=json.loads(json.dumps(config))
    changed["text_config"]["num_hidden_layers"]=28
    assert mlp_lower_bound(changed)!=mlp_lower_bound(config)


def test_ratio_requires_explicit_team_denominator_approval():
    from challenge.export.teacher_flops import comparison
    report=comparison(498640896,100000000000)
    assert report["core_flops_ratio"]==pytest.approx(0.00498640896)
    assert report["formal_ratio_pass"] is None
    assert report["team_denominator_approval"]=="PENDING"

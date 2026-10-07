"""Only the newly added candidate/scope arithmetic is checked here."""
from pathlib import Path
from challenge.export.flops_options import build_options


def test_candidate_scope_counts_and_ratios():
    r=build_options(Path(__file__).resolve().parents[2])
    assert r["student"]["arithmetic_total"] == 499437133
    assert r["student"]["arithmetic_plus_comparisons_total"] == 500219341
    assert r["teacher_counts"]["expanded_dominant_flops"] == 911695101952
    assert r["teacher_counts"]["exact_whole_network_flops"] is None
    assert len(r["candidates"]) == 4
    assert all(c["formal_ratio_pass"] is None for c in r["candidates"])
    assert all("ratio_upper_bound" not in c for c in r["candidates"])
    assert r["initial_prepared_package_evidence"]["same_as_fixed_teacher"]
    for c in r["candidates"]:
        assert c["ratio"] == c["numerator"]/c["denominator"]
        if c["id"].startswith("initial_student"):
            assert c["ratio"] == 1.0
            assert c["conditional_tier_points_if_baseline_and_scope_accepted"] == 0

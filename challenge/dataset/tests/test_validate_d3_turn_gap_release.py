from pathlib import Path

from challenge.dataset.validate_d3_turn_gap_release import validate_turn_gap_release


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "challenge/dataset/releases/d3_turn_gap_60_strict_v1"


def test_turn_gap_release_is_content_bound_strict_and_disjoint() -> None:
    report = validate_turn_gap_release(RELEASE, repo=ROOT, check_rgb=False)
    assert report["valid"] is True
    assert report["error_count"] == 0
    assert report["counts"] == {"train": 171, "val": 29, "hard_negative": 0}
    assert report["groups"] == {"train": 51, "val": 9, "hard_negative": 0}
    assert report["families"] == {
        "TC_C01_true_3step_left": 60,
        "TC_C02_yield_left_3step": 60,
        "TC_C03_true_4step_follow_left": 80,
    }
    assert report["locked_files_checked"] == 211
    assert report["evidence"]["signature_status"] == "CONTENT_BOUND_UNSIGNED"

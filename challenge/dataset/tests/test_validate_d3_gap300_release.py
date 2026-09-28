from __future__ import annotations

from pathlib import Path

from challenge.dataset.validate_d3_gap300_release import validate_release


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "challenge" / "dataset" / "releases" / "d3_gap300_strict_v1"


def test_gap300_release_is_portable_and_valid() -> None:
    report = validate_release(RELEASE, check_images=True)
    assert report["valid"] is True
    assert report["images_checked"] == 820
    assert report["splits"] == {
        "train": {"samples": 697, "groups": 238},
        "val": {"samples": 123, "groups": 42},
        "hard_negative": {"samples": 0, "groups": 0},
    }
    assert report["errors"] == []

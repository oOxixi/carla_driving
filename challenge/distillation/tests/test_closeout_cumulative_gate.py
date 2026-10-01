from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("torch")
yaml = pytest.importorskip("yaml")

from challenge.dataset.build_a3_closeout_cumulative_view import (  # noqa: E402
    build_closeout_cumulative_view,
)
from challenge.distillation.audit_closeout_cumulative_view import (  # noqa: E402
    audit_closeout_cumulative_view,
)
from challenge.distillation.train import _validate_frozen_identities  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
RELEASES = ROOT / "challenge" / "dataset" / "releases"
CLOSEOUT = ROOT / "challenge" / "dataset" / "governance" / "b1_closeout_v1"
FORMAL_CONFIG = (
    ROOT / "challenge" / "distillation" / "b1_closeout_final_formal_config.yaml"
)
SMOKE_CONFIG = (
    ROOT / "challenge" / "distillation" / "b1_closeout_final_smoke_config.yaml"
)


def _full_rgb_available() -> bool:
    expected = {
        "d3_wave1_addon_v1": 2363,
        "d3_wave2_safe_short_v1": 374,
        "d3_targeted_gap_strict_v1": 660,
        "d3_turn_gap_60_strict_v1": 200,
        "d3_gap300_strict_v1": 820,
        "b1_ms34_supplement_v1": 35,
    }
    return all(
        len(list((RELEASES / name / "images").glob("*.jpg"))) == count
        for name, count in expected.items()
    )


def _build(output: Path) -> dict:
    return build_closeout_cumulative_view(
        RELEASES / "d2_v1_1",
        RELEASES / "d3_wave1_addon_v1",
        RELEASES / "d3_wave2_safe_short_v1",
        RELEASES / "d3_targeted_gap_strict_v1",
        RELEASES / "d3_turn_gap_60_strict_v1",
        RELEASES / "d3_gap300_strict_v1",
        RELEASES / "b1_ms34_supplement_v1",
        CLOSEOUT,
        output,
        check_images=True,
    )


def _config(path: Path, view: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["dataset"]["train_path"] = str(view / "train.jsonl")
    config["dataset"]["val_path"] = str(view / "val.jsonl")
    config["dataset"]["view_manifest_path"] = str(
        view / "a3_closeout_view_manifest.json"
    )
    return config


def test_closeout_formal_view_is_reproducible_and_fail_closed(tmp_path: Path) -> None:
    if not _full_rgb_available():
        pytest.skip("full governed RGB releases are available on the training server")
    manifest = _build(tmp_path)
    assert manifest["counts"] == {
        "raw_governed_train": 6037,
        "raw_governed_dev": 1158,
        "train": 5856,
        "val": 1108,
        "excluded": 540,
        "ms34_train_addition": 30,
        "ms34_val_addition": 4,
        "ms34_hard_negative": 1,
    }
    assert manifest["plan_length_sample_counts"] == {
        "1": 6439,
        "2": 491,
        "3": 17,
        "4": 17,
    }
    assert manifest["policies"]["independent_validation_used"] is False
    assert manifest["policies"]["ms34_hard_negative_used_for_supervision"] is False

    config = _config(FORMAL_CONFIG, tmp_path)
    _validate_frozen_identities(config, integration_smoke=False)
    with pytest.raises(ValueError, match="cannot be used for integration smoke"):
        _validate_frozen_identities(config, integration_smoke=True)

    audit = audit_closeout_cumulative_view(
        RELEASES / "d2_v1_1",
        RELEASES / "d3_wave1_addon_v1",
        RELEASES / "d3_wave2_safe_short_v1",
        RELEASES / "d3_targeted_gap_strict_v1",
        RELEASES / "d3_turn_gap_60_strict_v1",
        RELEASES / "d3_gap300_strict_v1",
        RELEASES / "b1_ms34_supplement_v1",
        CLOSEOUT,
        tmp_path,
        check_images=True,
    )
    assert audit["status"] == "PASS"

    manifest_path = tmp_path / "a3_closeout_view_manifest.json"
    changed = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed["source_evidence_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="does not reproduce"):
        _validate_frozen_identities(config, integration_smoke=False)


def test_closeout_smoke_policy_cannot_become_formal(tmp_path: Path) -> None:
    if not _full_rgb_available():
        pytest.skip("full governed RGB releases are available on the training server")
    _build(tmp_path)
    config = _config(SMOKE_CONFIG, tmp_path)
    _validate_frozen_identities(config, integration_smoke=True)
    with pytest.raises(ValueError, match="limited to integration smoke"):
        _validate_frozen_identities(config, integration_smoke=False)

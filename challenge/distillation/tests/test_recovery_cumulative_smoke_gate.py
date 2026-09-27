from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("torch")
yaml = pytest.importorskip("yaml")

from challenge.dataset.build_a3_recovery_cumulative_view import (  # noqa: E402
    build_recovery_cumulative_view,
)
from challenge.distillation.train import _validate_frozen_identities  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
RELEASES = ROOT / "challenge" / "dataset" / "releases"
CONFIG = (
    ROOT / "challenge" / "distillation" / "d3_recovery_cumulative_smoke_config.yaml"
)


def _full_rgb_available() -> bool:
    expected = {
        "d3_wave1_addon_v1": 2363,
        "d3_wave2_safe_short_v1": 374,
        "d3_targeted_gap_strict_v1": 660,
        "d3_turn_gap_60_strict_v1": 200,
    }
    return all(
        len(list((RELEASES / name / "images").glob("*.jpg"))) == count
        for name, count in expected.items()
    )


def test_recovery_policy_is_reproducible_and_smoke_only(tmp_path: Path) -> None:
    if not _full_rgb_available():
        pytest.skip("full recovery RGB releases are available on the training server")
    build_recovery_cumulative_view(
        RELEASES / "d2_v1_1",
        RELEASES / "d3_wave1_addon_v1",
        RELEASES / "d3_wave2_safe_short_v1",
        RELEASES / "d3_targeted_gap_strict_v1",
        RELEASES / "d3_turn_gap_60_strict_v1",
        tmp_path,
        check_images=True,
    )
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["dataset"]["train_path"] = str(tmp_path / "train.jsonl")
    config["dataset"]["val_path"] = str(tmp_path / "val.jsonl")
    config["dataset"]["view_manifest_path"] = str(
        tmp_path / "a3_cumulative_view_manifest.json"
    )
    _validate_frozen_identities(config, integration_smoke=True)
    with pytest.raises(ValueError, match="limited to integration smoke"):
        _validate_frozen_identities(config, integration_smoke=False)

    manifest_path = tmp_path / "a3_cumulative_view_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_evidence_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="does not reproduce"):
        _validate_frozen_identities(config, integration_smoke=True)

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("torch")
yaml = pytest.importorskip("yaml")

from challenge.dataset.build_a3_final_cumulative_view import (  # noqa: E402
    build_final_cumulative_view,
)
from challenge.distillation.train import _validate_frozen_identities  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
RELEASES = ROOT / "challenge" / "dataset" / "releases"
FORMAL_CONFIG = (
    ROOT / "challenge" / "distillation" / "d3_final_cumulative_formal_config.yaml"
)
SMOKE_CONFIG = (
    ROOT / "challenge" / "distillation" / "d3_final_cumulative_smoke_config.yaml"
)


def _full_rgb_available() -> bool:
    expected = {
        "d3_wave1_addon_v1": 2363,
        "d3_wave2_safe_short_v1": 374,
        "d3_targeted_gap_strict_v1": 660,
        "d3_turn_gap_60_strict_v1": 200,
        "d3_gap300_strict_v1": 820,
    }
    return all(
        len(list((RELEASES / name / "images").glob("*.jpg"))) == count
        for name, count in expected.items()
    )


def _build(tmp_path: Path) -> None:
    build_final_cumulative_view(
        RELEASES / "d2_v1_1",
        RELEASES / "d3_wave1_addon_v1",
        RELEASES / "d3_wave2_safe_short_v1",
        RELEASES / "d3_targeted_gap_strict_v1",
        RELEASES / "d3_turn_gap_60_strict_v1",
        RELEASES / "d3_gap300_strict_v1",
        tmp_path,
        check_images=True,
    )


def _config(path: Path, tmp_path: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["dataset"]["train_path"] = str(tmp_path / "train.jsonl")
    config["dataset"]["val_path"] = str(tmp_path / "val.jsonl")
    config["dataset"]["view_manifest_path"] = str(
        tmp_path / "a3_final_view_manifest.json"
    )
    return config


def test_final_formal_policy_reproduces_exact_view(tmp_path: Path) -> None:
    if not _full_rgb_available():
        pytest.skip("full final RGB releases are available on the training server")
    _build(tmp_path)
    config = _config(FORMAL_CONFIG, tmp_path)
    _validate_frozen_identities(config, integration_smoke=False)
    with pytest.raises(ValueError, match="cannot be used for integration smoke"):
        _validate_frozen_identities(config, integration_smoke=True)

    manifest_path = tmp_path / "a3_final_view_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_evidence_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="does not reproduce"):
        _validate_frozen_identities(config, integration_smoke=False)


def test_final_smoke_policy_cannot_become_formal(tmp_path: Path) -> None:
    if not _full_rgb_available():
        pytest.skip("full final RGB releases are available on the training server")
    _build(tmp_path)
    config = _config(SMOKE_CONFIG, tmp_path)
    _validate_frozen_identities(config, integration_smoke=True)
    with pytest.raises(ValueError, match="limited to integration smoke"):
        _validate_frozen_identities(config, integration_smoke=False)

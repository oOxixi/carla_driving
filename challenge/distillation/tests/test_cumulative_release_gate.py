from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("torch")
yaml = pytest.importorskip("yaml")

from challenge.dataset.build_a3_cumulative_view import build_cumulative_view  # noqa: E402
from challenge.distillation.train import _validate_frozen_identities  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
D2 = ROOT / "challenge" / "dataset" / "releases" / "d2_v1_1"
D3 = ROOT / "challenge" / "dataset" / "releases" / "d3_wave1_addon_v1"
CONFIG = ROOT / "challenge" / "distillation" / "d2_d3_cumulative_formal_config.yaml"


def test_cumulative_formal_gate_requires_full_signed_inputs(tmp_path: Path) -> None:
    if len(list((D3 / "images").glob("*.jpg"))) != 2363:
        pytest.skip("full D3 RGB release is available on the formal training server")
    build_cumulative_view(D2, D3, tmp_path, check_d3_images=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["dataset"]["train_path"] = str(tmp_path / "train.jsonl")
    config["dataset"]["val_path"] = str(tmp_path / "val.jsonl")
    config["dataset"]["view_manifest_path"] = str(
        tmp_path / "a3_cumulative_view_manifest.json"
    )
    _validate_frozen_identities(config, integration_smoke=False)
    with pytest.raises(ValueError, match="cannot be used for integration smoke"):
        _validate_frozen_identities(config, integration_smoke=True)

    manifest_path = tmp_path / "a3_cumulative_view_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_evidence_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="source evidence digest mismatch"):
        _validate_frozen_identities(config, integration_smoke=False)

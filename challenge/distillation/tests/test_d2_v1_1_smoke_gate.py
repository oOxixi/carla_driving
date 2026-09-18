from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("torch")
yaml = pytest.importorskip("yaml")

from challenge.dataset.build_a3_d2_view import build_view  # noqa: E402
from challenge.distillation.train import _validate_frozen_identities  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "challenge" / "distillation" / "d2_v1_1_smoke_config.yaml"
RELEASE = ROOT / "challenge" / "dataset" / "releases" / "d2_v1_1"


def test_signed_d2_smoke_gate_checks_derived_view(tmp_path: Path) -> None:
    build_view(RELEASE, tmp_path)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["dataset"]["train_path"] = str(tmp_path / "train.jsonl")
    config["dataset"]["val_path"] = str(tmp_path / "val.jsonl")
    config["dataset"]["view_manifest_path"] = str(tmp_path / "a3_view_manifest.json")
    _validate_frozen_identities(config, integration_smoke=True)
    with pytest.raises(ValueError, match="limited to integration smoke"):
        _validate_frozen_identities(config, integration_smoke=False)

    manifest_path = tmp_path / "a3_view_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_release_manifest_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match signed B1 release"):
        _validate_frozen_identities(config, integration_smoke=True)

import json
from pathlib import Path

import pytest
import yaml

from tools.verify_model_manifest import verify_profile


ROOT = Path(__file__).resolve().parents[2]


def test_compose_has_offline_three_service_boundary() -> None:
    compose = yaml.safe_load((ROOT / "docker/compose.yaml").read_text(encoding="utf-8"))
    assert set(compose["services"]) == {"carla", "qwen", "controller"}
    assert compose["services"]["controller"]["environment"]["QWEN_BASE_URL"] == "http://qwen:8001/v1"
    rendered = (ROOT / "docker/compose.yaml").read_text(encoding="utf-8")
    assert "../artifacts" not in rendered
    assert "huggingface" not in rendered.lower()
    assert "F:\\" not in rendered
    assert compose["services"]["controller"]["depends_on"]["qwen"]["condition"] == "service_healthy"


def test_model_profile_verifier_rejects_hash_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "model"
    root.mkdir()
    (root / "config.json").write_text("{}", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"models": [{
        "profile": "qwen3vl-2b-int4",
        "files": [{"path": "config.json", "bytes": 2, "sha256": "0" * 64}],
    }]}), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256"):
        verify_profile(manifest, root, "qwen3vl-2b-int4")

import json
from pathlib import Path

import pytest
import yaml

from tools.create_qwen_launch_logs import create_launch_logs
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


def test_offline_images_do_not_copy_the_entire_build_context() -> None:
    controller = (ROOT / "docker/Dockerfile.controller").read_text(encoding="utf-8")
    assert "COPY . /app" not in controller
    assert "COPY integration/ /app/integration/" in controller
    assert "scenario-runner.lock.json" in controller
    qwen = (ROOT / "docker/Dockerfile.qwen-cu132").read_text(encoding="utf-8")
    assert "vllm.lock.json" in qwen
    assert "verify_release_lock.py" in qwen
    assert "REPRO_OUTPUT_ROOT: /output/runs" in (ROOT / "docker/compose.yaml").read_text(encoding="utf-8")


def test_qwen_launch_logs_are_fresh_uuid_scoped_and_not_user_controlled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEN_LAUNCH_ID", "injected-old-launch")
    old = tmp_path / "qwen-evidence-injected-old-launch.log"
    old.write_text("QWEN_LAUNCH_BEGIN launch_id=injected-old-launch\nQWEN_LAUNCH_END launch_id=injected-old-launch\n")
    launch_id = create_launch_logs(tmp_path)
    assert launch_id != "injected-old-launch"
    assert (tmp_path / f"qwen-evidence-{launch_id}.log").read_text(encoding="utf-8") == ""

    entrypoint = (ROOT / "docker/entrypoints/qwen.sh").read_text(encoding="utf-8")
    assert "QWEN_LAUNCH_ID" not in entrypoint
    assert "qwen-evidence-$launch_id.log" in entrypoint
    assert "kill -0 \"$vllm_pid\"" in entrypoint


def test_qwen_launch_log_collision_cannot_append_or_reuse_evidence(tmp_path: Path) -> None:
    from uuid import UUID

    launch_id = UUID("12345678-1234-5678-1234-567812345678")
    create_launch_logs(tmp_path, launch_id)
    evidence = tmp_path / f"qwen-evidence-{launch_id}.log"
    evidence.write_text("old ready evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="collision"):
        create_launch_logs(tmp_path, launch_id)
    assert evidence.read_text(encoding="utf-8") == "old ready evidence"


def test_qwen_requirement_uses_the_staged_wheel_metadata_version() -> None:
    lock = json.loads((ROOT / "third_party/vllm.lock.json").read_text(encoding="utf-8"))
    requirements = (ROOT / "docker/requirements-qwen.txt").read_text(encoding="utf-8").splitlines()
    assert f"vllm=={lock['expected_wheel_version']}" in requirements


def test_controller_voice_uses_available_matched_cu132_torch_pair() -> None:
    requirements = (ROOT / "docker/requirements-voice.txt").read_text(encoding="utf-8").splitlines()
    assert requirements[:2] == ["torch==2.11.0+cu132", "torchaudio==2.11.0+cu132"]

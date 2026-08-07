from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.build_submission_package import check_release
from tools.repro_cli import (
    EvaluationDecision,
    _scenario_command,
    build_evaluation_steps,
    parse_args,
)


ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_latency_first_contract_and_explicit_modes() -> None:
    assert build_evaluation_steps() == [
        "preflight", "warmup", "latency_gate", "accuracy", "scenarios"
    ]
    assert EvaluationDecision.from_latency_p95(300.0).remaining_steps == ["accuracy", "scenarios"]
    assert EvaluationDecision.from_latency_p95(300.01).status == "EARLY_STOP"
    assert parse_args(["evaluate"]).mode == "evaluate"


def test_host_wrappers_only_launch_python_inside_docker() -> None:
    shell = (ROOT / "run.sh").read_text(encoding="utf-8")
    powershell = (ROOT / "run.ps1").read_text(encoding="utf-8")
    assert "docker compose" in shell and "python3 -m tools.repro_cli" in shell
    assert "python tools.repro_cli" not in shell
    assert "'python3','-m','tools.repro_cli'" in powershell
    assert "docker @base @cli" in powershell


def test_carla_scenario_uses_remote_vllm_contract() -> None:
    command = _scenario_command(Path("/data"), "scenario.json", Path("/output"))
    assert "--qwen-remote" in command
    assert "--qwen-base-url" in command
    assert "--qwen-model" in command
    assert "--realtime" in command
    assert "--qwen-service-url" not in command
    assert "--audio" not in command


def test_reference_values_and_raw_files_are_source_backed() -> None:
    source = ROOT / "artifacts/B_role_validation"
    reference = ROOT / "metrics/reference_5070"
    latency_name = "qwen3vl_2b_gptq_int4_marlin_vllm_cu132_latency_gate_prompt_v3.json"
    contract_name = "qwen3vl_2b_gptq_int4_marlin_vllm_cu132_target10_prompt_v3.json"
    latency_raw = json.loads((source / latency_name).read_text(encoding="utf-8"))
    contract_raw = json.loads((source / contract_name).read_text(encoding="utf-8"))
    latency = json.loads((reference / "metrics/latency.json").read_text(encoding="utf-8"))
    accuracy = json.loads((reference / "metrics/accuracy.json").read_text(encoding="utf-8"))
    assert latency["p50_ms"] == latency_raw["latency_ms"]["p50_ms"]
    assert latency["p95_ms"] == latency_raw["latency_ms"]["p95_ms"]
    assert latency["max_ms"] == latency_raw["latency_ms"]["max_ms"]
    assert accuracy["proxy_contract"]["accuracy"] == contract_raw["metrics"]["all_contract_accuracy"]
    assert accuracy["proxy_contract"]["passed"] == 10
    assert accuracy["official_asr"]["status"] == "NOT_RUN"
    assert _sha256(source / latency_name) == _sha256(reference / "raw" / latency_name)
    assert _sha256(source / contract_name) == _sha256(reference / "raw" / contract_name)


def test_docs_notebook_handoff_and_missing_artifacts_are_honest() -> None:
    notebook = json.loads((ROOT / "notebooks/reproduce.ipynb").read_text(encoding="utf-8"))
    code = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"] if cell["cell_type"] == "code")
    assert "RUN_DIR" in code
    assert "pip install" not in code and "from_pretrained" not in code
    handoff = (ROOT / "HANDOFF_B_REPRO_0804.md").read_text(encoding="utf-8")
    for section in ("Scope", "Default Route", "RTX 5070 Results", "A800 Status", "Evidence Index", "Reproduction", "Known Limits", "Next Operator"):
        assert f"## {section}" in handoff
    assert "A800" in handoff and "NOT_RUN" in handoff
    missing = check_release(ROOT)
    assert any("image.tar missing" in item for item in missing)
    assert any("technical solution PDF missing" in item for item in missing)
    assert any("CARLA demo video missing" in item for item in missing)


def test_empty_release_files_do_not_pass_check(tmp_path: Path) -> None:
    for relative in (
        "release_assets/weights/qwen3vl-2b-int4/model.bin",
        "release_assets/weights/asr/SenseVoiceSmall/model.bin",
        "metrics/reference_5070/run_manifest.json",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
    for relative in (
        "dist/carla-language-control-submission/image.tar",
        "submission/技术方案.pdf",
        "submission/demo/carla_closed_loop.mp4",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    missing = check_release(tmp_path)
    assert any("image.tar is empty" in item for item in missing)
    assert any("technical solution PDF is empty" in item for item in missing)
    assert any("CARLA demo video is empty" in item for item in missing)


def test_weight_downloads_target_release_assets() -> None:
    primary = (ROOT / "weights/download_fallback.sh").read_text(encoding="utf-8")
    asr = (ROOT / "weights/download_asr_fallback.sh").read_text(encoding="utf-8")
    optional = (ROOT / "weights/download_optional_models.sh").read_text(encoding="utf-8")
    assert "release_assets/weights" in primary
    assert "release_assets/weights" in asr and '}/asr' in asr
    assert "release_assets/weights" in optional and '}/optional' in optional

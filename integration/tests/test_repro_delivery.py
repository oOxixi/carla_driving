from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.build_submission_package import check_release
from tools.repro_cli import EvaluationDecision, build_evaluation_steps, parse_args


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

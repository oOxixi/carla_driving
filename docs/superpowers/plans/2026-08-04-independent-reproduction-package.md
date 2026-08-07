# Independent CARLA Reproduction Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained CARLA voice/multimodal competition package that runs end-to-end on the local RTX 5070 and can be loaded and evaluated immediately on an A800 with CUDA 13.2, without editing code, compiling, or downloading the primary model.

**Architecture:** Keep `qwen3vl-2b-int4` as the default inference profile and expose Qwen only through an OpenAI-compatible service. Package CARLA, the controller, and Qwen/vLLM as three pinned Docker images; a single orchestration CLI creates one run directory and records immutable environment, model, latency, accuracy, scenario, log, and media evidence. Selectively import only model-neutral ScenarioRunner, benchmark-audit, target-repair, and staged-timing work from `team/8.4-xky-3B`; 3B remains an optional A800 comparison profile.

**Tech Stack:** Python 3.12, pytest, CARLA 0.9.16, ScenarioRunner 0.9.16, Qwen3-VL 2B GPTQ INT4/Marlin, vLLM built for CUDA 13.2, Docker Compose, Bash/PowerShell, JSON/JSONL, Jupyter, ffmpeg.

## Global Constraints

- Default model profile is `qwen3vl-2b-int4`; `qwen3vl-2b-fp8` and `qwen25vl-3b-bf16` are opt-in comparisons only.
- ASR is fixed to `iic/SenseVoiceSmall` revision `7bf452403abd7353a300cd760f7adae7701c92c1` with the active dialect LoRA SHA256 `38d541099157ba5c35d8256f2ebd8a374cae85a5ca7eb9b2a7cb8a033c624de1`.
- ScenarioRunner is fixed to CARLA-compatible commit `94ff3b8af752bad2b9d464ad5105868906aa34c0` and is embedded in the controller image.
- The primary image contains the fixed 2B INT4 weights and never relies on a host Hugging Face cache or `F:\carla_driving_rstar` path.
- A800 reproduction uses CUDA 13.2 userspace, performs no source compilation, and makes no primary-model network download.
- Docker archive `image.tar` contains exactly the CARLA 0.9.16, controller, and selected Qwen/vLLM images needed by the release.
- Official gates are instruction parsing P95 `<= 50 ms`, end-to-end P95 `<= 150 ms`, voice semantic accuracy `>= 95%`, multimodal contract accuracy `>= 98%`, and three-class scenario completion `>= 90%`.
- End-to-end P95 `> 300 ms` is an internal early-stop condition; it is not an official passing threshold, and accuracy/stability suites must not run after it triggers.
- A latency gate uses 5 warm-up requests followed by 10 measured requests with dynamic frames; fixed-image hot latency is diagnostic only.
- Every run records mean, P50, P95, P99, and max for `asr_ms`, `instruction_parse_ms`, `asr_nlu_ms`, `sensor_fusion_ready_ms`, `qwen_service_ms`, `post_qwen_control_ms`, and `end_to_end_ms`; the official `<= 50 ms` parsing gate applies to `instruction_parse_ms`, not to audio decoding plus ASR.
- The 6192-record language benchmark is a language/schema regression set, not 6192 physical CARLA scenarios; formal accuracy uses the frozen validation split only.
- Failed samples remain in raw evidence. Expected actions and scoring rules cannot be edited after results are observed.
- Qwen produces a high-level action contract only; target binding and final throttle/brake/steering continue through the existing deterministic safety arbiter.
- RTX 5070 results are labeled as 5070 reference evidence and never reported as A800 measurements.
- Do not import the 3B branch's CUDA 13.0 launcher, port 8002 default, 3B default model, or reports whose referenced raw JSON/log evidence is absent.
- Preserve existing user changes and untracked artifacts. Stage only files named in the current task.
- Run the narrow test named in each red/green cycle; run the consolidated regression once in Task 11 instead of repeating unrelated suites.

---

## File Structure

### Model and inference boundary

- `integration/qwen_profiles.py`: immutable model/profile registry and environment resolution.
- `integration/qwen_vl_adapter.py`: strict action schema and profile-specific compact prompt rendering.
- `integration/qwen_remote_backend.py`: OpenAI-compatible client that receives a resolved profile.
- `integration/carla_runner.py`: model-neutral scenario semantics, target binding, and controller bridge.
- `integration/scenario_runner_agent.py`: official ScenarioRunner `--agent` entry point.

### Evidence and evaluation

- `integration/run_manifest.py`: atomic run-directory lifecycle and environment/model provenance.
- `tools/four_modal_metrics.py`: common percentile and correctness aggregation.
- `tools/run_four_modal_full_chain.py`: offline/frozen full-chain evaluator using local or remote Qwen.
- `tools/repro_cli.py`: preflight, smoke, evaluate, demo, stability, and stop orchestration.
- `CARLA-Language-Benchmark/`: frozen language data, provenance, audit, and label-repair assets imported from the 3B branch.

### Offline runtime and release

- `docker/Dockerfile.controller`: CUDA 13.2 controller/ASR runtime with source and frozen non-Qwen assets.
- `docker/Dockerfile.qwen-cu132`: CUDA 13.2 runtime containing a prebuilt vLLM wheel and fixed Qwen weights.
- `docker/compose.yaml`: CARLA, Qwen, and controller services with health checks and no development mounts.
- `docker/entrypoints/qwen.sh`: validates manifests and starts the OpenAI-compatible endpoint.
- `config/repro/*.env`: common, RTX 5070, A800-safe, and A800-optimized settings.
- `run.sh`, `stop.sh`, `run.ps1`, `stop.ps1`: thin cross-platform entry points around `tools/repro_cli.py`.
- `tools/build_submission_package.py`: validates assets, creates `image.tar`, writes hashes, and assembles the release directory.

### Human-facing reproduction artifacts

- `README_REPRO.md`: exact environment, input/output, commands, expected files, thresholds, and troubleshooting.
- `notebooks/reproduce.ipynb`: reads an existing run, verifies manifests, and renders metrics without installing dependencies.
- `submission/technical_solution.md` and `submission/技术方案.pdf`: source and rendered technical explanation.
- `tools/render_closed_loop_video.py`: deterministic video composition with command/action/result overlays.
- `submission/demo/carla_closed_loop.mp4`: physical CARLA closed-loop evidence generated from one run.

---

### Task 1: Freeze and Audit the Model-Neutral Language Benchmark

**Files:**
- Create: `integration/tests/test_language_benchmark_release.py`
- Create: `CARLA_Language_Benchmark/__init__.py`
- Create: `CARLA_Language_Benchmark/tools/__init__.py`
- Create: `CARLA_Language_Benchmark/tools/audit_global_benchmark_v1.py`
- Create: `tools/benchmark_audit.py`
- Restore from `team/8.4-xky-3B`: `CARLA-Language-Benchmark/`
- Modify after restore: `CARLA-Language-Benchmark/tools/audit_global_benchmark_v1.py`
- Restore from `team/8.4-xky-3B`: `tools/build_qwen_four_modal_stress_set.py`
- Restore from `team/8.4-xky-3B`: `qwen_service/tests/test_stress_set_semantic_repair.py`

**Interfaces:**
- Consumes: Git ref `team/8.4-xky-3B` at `94eea04`.
- Produces: `CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json`, `CARLA-Language-Benchmark/dataset_card.json`, `CARLA-Language-Benchmark/baseline/freeze_p0/dataset_checksum.json`, and an audit command that exits nonzero on duplicate IDs, missing fields, invalid actions, record-count mismatch, or checksum mismatch.

- [ ] **Step 1: Write the failing release-integrity test**

```python
from __future__ import annotations

import json
from pathlib import Path

from CARLA_Language_Benchmark.tools.audit_global_benchmark_v1 import audit_dataset


ROOT = Path(__file__).resolve().parents[2]


def test_language_benchmark_is_frozen_and_repairable() -> None:
    benchmark = ROOT / "CARLA-Language-Benchmark"
    data_path = benchmark / "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json"
    card_path = benchmark / "dataset_card.json"
    checksum_path = benchmark / "baseline/freeze_p0/dataset_checksum.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))
    card = json.loads(card_path.read_text(encoding="utf-8"))
    checksum = json.loads(checksum_path.read_text(encoding="utf-8"))
    report = audit_dataset(data_path)

    assert card["release_status"] == "frozen_baseline"
    assert card["total_records"] == len(rows) == 6192
    assert len({row["id"] for row in rows}) == 6192
    assert all(row["expected_action"] for row in rows)
    assert report["errors"] == 0
    assert checksum["path"] == "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json"
    assert checksum["records"] == 6192
    assert checksum["sha256"] == report["sha256"]
```

Because the directory name contains hyphens, add a package-safe wrapper at `CARLA_Language_Benchmark/tools/audit_global_benchmark_v1.py` that imports the audited implementation from `tools/benchmark_audit.py`; do not use dynamic path injection in the test.

- [ ] **Step 2: Run the test and confirm the benchmark is not yet present on the target branch**

Run: `python -m pytest integration/tests/test_language_benchmark_release.py -q`

Expected: FAIL during collection because the package-safe benchmark audit wrapper is absent.

- [ ] **Step 3: Restore only benchmark, audit, provenance, and semantic-repair assets**

```powershell
git restore --source team/8.4-xky-3B -- CARLA-Language-Benchmark tools/build_qwen_four_modal_stress_set.py qwen_service/tests/test_stress_set_semantic_repair.py
```

Create `tools/benchmark_audit.py` with `audit_dataset(path: Path) -> dict[str, object]`. Move the branch script's field/action checks into that function, add SHA256, return the report, and make its CLI exit 1 when `errors != 0`. Its CLI accepts the positional dataset path, `--write-checksum PATH`, and `--checksum PATH`; checksum verification adds one error and exits 1 on mismatch. Both `CARLA-Language-Benchmark/tools/audit_global_benchmark_v1.py` and `CARLA_Language_Benchmark/tools/audit_global_benchmark_v1.py` expose the shared implementation with:

```python
from tools.benchmark_audit import audit_dataset, main


if __name__ == "__main__":
    raise SystemExit(main())
```

The checksum writer is:

```python
def write_checksum(data_path: Path, output_path: Path) -> None:
    report = audit_dataset(data_path)
    payload = {
        "path": "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json",
        "records": report["records"],
        "sha256": report["sha256"],
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
```

Generate `CARLA-Language-Benchmark/baseline/freeze_p0/dataset_checksum.json` once with the new CLI. This generated checksum is reviewable source data and is committed with the benchmark.

Run: `python -m tools.benchmark_audit CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json --write-checksum CARLA-Language-Benchmark/baseline/freeze_p0/dataset_checksum.json`

Expected: exit code 0 and the checksum JSON contains 6192 records.

- [ ] **Step 4: Run the narrow audit and repair tests**

Run: `python -m pytest integration/tests/test_language_benchmark_release.py qwen_service/tests/test_stress_set_semantic_repair.py -q`

Expected: PASS, with 6192 unique benchmark rows and both inconsistent/consistent target-repair cases preserved by tests.

- [ ] **Step 5: Run the branch-provided benchmark audit once**

Run: `python CARLA-Language-Benchmark/tools/audit_global_benchmark_v1.py CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json --checksum CARLA-Language-Benchmark/baseline/freeze_p0/dataset_checksum.json`

Expected: exit code 0; the summary reports 6192 records and zero schema/ID errors.

- [ ] **Step 6: Commit only the frozen benchmark deliverable**

```powershell
git add CARLA-Language-Benchmark CARLA_Language_Benchmark tools/benchmark_audit.py tools/build_qwen_four_modal_stress_set.py integration/tests/test_language_benchmark_release.py qwen_service/tests/test_stress_set_semantic_repair.py
git commit -m "data: freeze audited language benchmark"
```

### Task 2: Add an Immutable Model Profile Registry and Compact 2B Prompt

**Files:**
- Create: `integration/qwen_profiles.py`
- Create: `integration/tests/test_qwen_profiles.py`
- Modify: `integration/qwen_vl_adapter.py`
- Modify: `integration/qwen_remote_backend.py`
- Modify: `tools/run_qwen_latency_gate.py`
- Test: `integration/tests/test_qwen_vl_adapter.py`
- Test: `integration/tests/test_qwen_remote_backend.py`

**Interfaces:**
- Consumes: environment variable `QWEN_PROFILE` and optional explicit profile name.
- Produces: `QwenModelProfile`, `get_qwen_profile(name: str) -> QwenModelProfile`, `resolve_qwen_profile(name: str | None) -> QwenModelProfile`, and `build_action_choice_prompt(context: QwenInputContext, *, prompt_style: str = "compact-v2") -> str` while retaining one-token A–E output and deterministic strict-Schema assembly.

- [ ] **Step 1: Write failing profile and default-safety tests**

```python
import pytest

from integration.qwen_profiles import get_qwen_profile, resolve_qwen_profile


def test_default_profile_is_2b_int4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QWEN_PROFILE", raising=False)
    profile = resolve_qwen_profile(None)
    assert profile.name == "qwen3vl-2b-int4"
    assert profile.quantization == "gptq"
    assert profile.required_linear_kernel == "MarlinLinearKernel"
    assert profile.image_max_side == 256
    assert profile.visual_tokens == 64
    assert profile.port == 8001


def test_3b_is_explicit_and_never_the_default() -> None:
    profile = get_qwen_profile("qwen25vl-3b-bf16")
    assert profile.model == "Qwen/Qwen2.5-VL-3B-Instruct"
    assert profile.optional is True


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported Qwen profile"):
        get_qwen_profile("fastest")
```

- [ ] **Step 2: Run the new tests to verify the registry is missing**

Run: `python -m pytest integration/tests/test_qwen_profiles.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: integration.qwen_profiles`.

- [ ] **Step 3: Implement the immutable registry**

```python
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QwenModelProfile:
    name: str
    model: str
    revision: str
    quantization: str
    required_linear_kernel: str | None
    image_max_side: int
    visual_tokens: int
    port: int
    prompt_style: str
    optional: bool


_PROFILES = {
    "qwen3vl-2b-int4": QwenModelProfile(
        name="qwen3vl-2b-int4",
        model="h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4",
        revision="f91db2369bd00e7ec20bf09b6a0080cdb26aefa5",
        quantization="gptq",
        required_linear_kernel="MarlinLinearKernel",
        image_max_side=256,
        visual_tokens=64,
        port=8001,
        prompt_style="compact-v2",
        optional=False,
    ),
    "qwen3vl-2b-fp8": QwenModelProfile(
        name="qwen3vl-2b-fp8",
        model="Qwen/Qwen3-VL-2B-Instruct-FP8",
        revision="46485250d8854c0a9be4f1adbc67ca47e5bb6fa5",
        quantization="fp8",
        required_linear_kernel=None,
        image_max_side=256,
        visual_tokens=64,
        port=8001,
        prompt_style="compact-v2",
        optional=True,
    ),
    "qwen25vl-3b-bf16": QwenModelProfile(
        name="qwen25vl-3b-bf16",
        model="Qwen/Qwen2.5-VL-3B-Instruct",
        revision="66285546d2b821cf421d4f5eb2576359d3770cd3",
        quantization="bf16",
        required_linear_kernel=None,
        image_max_side=224,
        visual_tokens=256,
        port=8002,
        prompt_style="compact-v2",
        optional=True,
    ),
}


def get_qwen_profile(name: str) -> QwenModelProfile:
    try:
        return _PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unsupported Qwen profile: {name}") from exc


def resolve_qwen_profile(name: str | None) -> QwenModelProfile:
    return get_qwen_profile(name or os.getenv("QWEN_PROFILE", "qwen3vl-2b-int4"))
```

```python
def test_all_revisions_are_immutable() -> None:
    for name in ("qwen3vl-2b-int4", "qwen3vl-2b-fp8", "qwen25vl-3b-bf16"):
        assert get_qwen_profile(name).revision not in {"main", "master", "latest"}
```

- [ ] **Step 4: Add a compact, strict prompt regression before changing prompt code**

```python
def test_compact_prompt_keeps_schema_and_safety_rules() -> None:
    context = QwenInputContext(
        request_id="prompt-1",
        frame=1,
        sim_time_s=0.05,
        voice_command="前方车辆旁边停车",
        scene_state={"ego_speed_mps": 8.0, "unused_debug_trace": "x" * 500},
        perception={"visual_valid": True, "detected_objects": []},
        safety_state={"recommended_action": "STOP", "reason": "target_missing"},
        rgb_ref=None,
    )
    prompt = build_action_choice_prompt(
        context,
        prompt_style="compact-v2",
    )
    assert len(prompt.encode("utf-8")) < 1800
    assert "A=START" in prompt and "E=EMERGENCY_STOP" in prompt
    assert "只输出一个代码" in prompt
    assert "安全规则" in prompt
    assert "unused_debug_trace" not in prompt
```

Run: `python -m pytest integration/tests/test_qwen_vl_adapter.py::test_compact_prompt_keeps_schema_and_safety_rules -q`

Expected: FAIL because `prompt_style` is not accepted or the prompt exceeds the byte budget.

- [ ] **Step 5: Implement `compact-v2` without weakening deterministic strict-Schema assembly**

```python
def build_action_choice_prompt(
    context: QwenInputContext, *, prompt_style: str = "compact-v2"
) -> str:
    if prompt_style != "compact-v2":
        raise ValueError(f"unsupported Qwen prompt style: {prompt_style}")
    compact = _compact_action_context(context)
    return (
        "融合图像与四模态状态，只输出一个代码，禁止解释或底层控制。"
        "A=START；B=STOP；C=SLOW_DOWN；D=SET_SPEED；E=EMERGENCY_STOP。"
        "优先级：安全规则>明确语音动作>普通视觉线索；普通车辆本身不是停车风险。"
        "红灯或安全模块要求停车选B；TTC不大于2秒或紧急危险选E。"
        "明确跟随或避让且无停车风险选C；明确设置速度选D。"
        "目标缺失、视觉无效、语义冲突或不确定时选B。输入="
        + json.dumps(compact, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    )
```

`_compact_action_context()` must retain only voice text, ego speed/behavior, traffic light/collision/visual validity, detected-object `track_id/class/relation/distance_m/confidence/bbox_xyxy_norm`, LiDAR validity/front-corridor distance/point count, and safety recommendation/TTC/reason. The model still emits one A–E token; `assemble_action_choice()` remains the only producer of the strict action dictionary, target ID, confidence/confirmation fields, and safety override.

- [ ] **Step 6: Inject resolved profiles into the remote backend and latency gate**

Make the backend constructor explicit while preserving existing call sites:

```python
def __init__(
    self,
    *,
    base_url: str,
    profile: QwenModelProfile | None = None,
    api_key: str = "local-offline",
    timeout_s: float = 30.0,
) -> None:
    self.profile = profile or resolve_qwen_profile(None)
    self.base_url = base_url.rstrip("/")
    self.timeout_s = timeout_s
    self.prompt_style = self.profile.prompt_style
```

In `StrictQwenVLAdapter.infer`, render the one-token prompt with the backend's declared style:

```python
prompt = build_action_choice_prompt(
    context,
    prompt_style=getattr(self._backend, "prompt_style", "compact-v2"),
)
```

Add a regression where a fake backend sets `prompt_style="compact-v2"`, returns `QwenVLActionChoice("B", "STOP", 0.99)`, and assert the final adapter result is still the existing strict dictionary with `action="STOP"`, `requires_confirmation`, confidence, decision source, and no low-level control fields.

Change `tools/run_qwen_latency_gate.py` so `--profile` defaults to `qwen3vl-2b-int4`, the model/revision/image budget come from `resolve_qwen_profile(args.profile)`, and explicit `--model` is removed from the official gate path.

In `OpenAICompatibleQwenVLBackend.generate_action`, pass the fixed remote visual budget with the existing constrained-output body:

```python
"mm_processor_kwargs": {
    "min_pixels": self.profile.visual_tokens * 28 * 28,
    "max_pixels": self.profile.visual_tokens * 28 * 28,
},
```

Extend the fake-client assertion to require both values equal `64 * 28 * 28` for the default profile, along with `max_tokens=1` and `structured_outputs.choice == ["A", "B", "C", "D", "E"]`.

- [ ] **Step 7: Run the focused profile, prompt, backend, and gate tests**

Run: `python -m pytest integration/tests/test_qwen_profiles.py integration/tests/test_qwen_vl_adapter.py integration/tests/test_qwen_remote_backend.py integration/tests/test_qwen_latency_gate.py -q`

Expected: PASS; no test starts a real model server.

- [ ] **Step 8: Commit the profile boundary**

```powershell
git add integration/qwen_profiles.py integration/qwen_vl_adapter.py integration/qwen_remote_backend.py tools/run_qwen_latency_gate.py integration/tests/test_qwen_profiles.py integration/tests/test_qwen_vl_adapter.py integration/tests/test_qwen_remote_backend.py integration/tests/test_qwen_latency_gate.py
git commit -m "feat: pin Qwen profiles and compact strict prompt"
```

### Task 3: Integrate ScenarioRunner and Unseen-Scenario Generalization

**Files:**
- Restore selectively: `integration/scenario_runner_agent.py`
- Restore selectively: `integration/tests/test_unseen_scenario_generalization.py`
- Modify selectively: `integration/carla_runner.py`
- Modify: `integration/tests/test_official_scenario_runner.py`
- Modify: `integration/tests/test_carla_runner_helpers.py`
- Modify: `scripts/run_scenario_runner.ps1`

**Interfaces:**
- Consumes: `resolve_qwen_profile()` from Task 2 and existing `ScenarioEvidenceRecorder`/safety arbiter.
- Produces: ScenarioRunner class `CarlaLanguageAgent`, `derive_runtime_scenario_profile(expected_contract: dict, scenario_text: str) -> RuntimeScenarioProfile`, and model-neutral behavior for unknown scenario IDs.

- [ ] **Step 1: Restore the branch's regression tests first**

```powershell
git restore --source team/8.4-xky-3B -- integration/tests/test_unseen_scenario_generalization.py integration/tests/test_official_scenario_runner.py
```

- [ ] **Step 2: Run the ScenarioRunner tests and confirm the missing agent/generalization behavior**

Run: `python -m pytest integration/tests/test_unseen_scenario_generalization.py integration/tests/test_official_scenario_runner.py -q`

Expected: FAIL because `integration.scenario_runner_agent` or generalized scenario helpers are absent.

- [ ] **Step 3: Restore the official agent and obtain the exact shared-runner diff for review**

```powershell
git restore --source team/8.4-xky-3B -- integration/scenario_runner_agent.py
git diff carla_driving_rstar..team/8.4-xky-3B -- integration/carla_runner.py
```

Apply only hunks that derive behavior from scenario content/expected contracts, preserve evaluator-owned actors, handle missing targets, or support `scenario_runner_agent.py`. Do not apply hunks changing model names, revisions, ports, CUDA versions, or evidence paths.

- [ ] **Step 4: Add a default-model guard before editing the shared runner**

```python
import json
from pathlib import Path


def test_carla_runner_does_not_hardcode_optional_model_defaults() -> None:
    source = (Path(__file__).parents[1] / "carla_runner.py").read_text(encoding="utf-8")
    assert "Qwen/Qwen2.5-VL-3B-Instruct" not in source
    assert "66285546d2b821cf421d4f5eb2576359d3770cd3" not in source
    assert "localhost:8002" not in source
```

- [ ] **Step 5: Implement the model-neutral runtime profile boundary**

Use this focused type and precedence in `integration/carla_runner.py`:

```python
@dataclass(frozen=True, slots=True)
class RuntimeScenarioProfile:
    behavior: str
    requires_target: bool
    emergency: bool
    completion_key: str


def derive_runtime_scenario_profile(
    expected_contract: dict[str, object], scenario_text: str
) -> RuntimeScenarioProfile:
    action = str(expected_contract.get("action", "STOP")).upper()
    text = scenario_text.lower()
    emergency = action in {"STOP", "YIELD"} and any(
        token in text for token in ("emergency", "pedestrian", "cut-in", "应急", "行人")
    )
    requires_target = action in {"PARK", "YIELD", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT"}
    return RuntimeScenarioProfile(
        behavior=action,
        requires_target=requires_target,
        emergency=emergency,
        completion_key="safe_stop" if emergency else "route_progress",
    )
```

Unknown IDs must use this function instead of falling back to a known ID. If `requires_target` is true and no target is bound, emit the existing fail-closed STOP contract and record `failure_reason="missing_required_target"`.

- [ ] **Step 6: Make the launcher resolve the agent path without a repository absolute path**

In `scripts/run_scenario_runner.ps1`, compute the root from the script itself and pass:

```powershell
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$agentPath = Join-Path $repoRoot 'integration/scenario_runner_agent.py'
& $pythonExe $scenarioRunnerScript --agent $agentPath --agentConfig $AgentConfig @scenarioArgs
```

- [ ] **Step 7: Run only ScenarioRunner/helper regressions**

Run: `python -m pytest integration/tests/test_unseen_scenario_generalization.py integration/tests/test_official_scenario_runner.py integration/tests/test_carla_runner_helpers.py -q`

Expected: PASS, including unknown ID, evaluator-owned actor, target-missing, and safety-conflict cases.

- [ ] **Step 8: Commit the model-neutral ScenarioRunner integration**

```powershell
git add integration/scenario_runner_agent.py integration/carla_runner.py integration/tests/test_unseen_scenario_generalization.py integration/tests/test_official_scenario_runner.py integration/tests/test_carla_runner_helpers.py scripts/run_scenario_runner.ps1
git commit -m "feat: integrate model-neutral ScenarioRunner agent"
```

### Task 4: Standardize Run Manifests, Stage Timing, and Metric Gates

**Files:**
- Create: `integration/run_manifest.py`
- Create: `integration/tests/test_run_manifest.py`
- Modify: `tools/four_modal_metrics.py`
- Modify: `tools/run_four_modal_full_chain.py`
- Create: `integration/tests/test_four_modal_full_chain_remote.py`
- Modify: `integration/tests/test_qwen_four_modal_stress_set.py`
- Create: `datasets/repro/full_chain_latency_v1.json`

**Interfaces:**
- Consumes: `QwenModelProfile`, the 250-file voice manifest, the 320-case text/RGB/LiDAR contract set, a 10-pair real-audio/dynamic-frame latency manifest, frozen dataset SHA256, Git commit, Docker image digests, and per-sample stage timings.
- Produces: `RunContext`, `begin_run(output_root: Path, metadata: dict) -> RunContext`, `finish_run(context: RunContext, status: str, failure_reason: str | None) -> None`, `summarize_latency(values: list[float]) -> dict[str, float]`, and `evaluate_official_gates(metrics: dict) -> dict[str, object]`.

- [ ] **Step 1: Write the failing manifest lifecycle test**

```python
from pathlib import Path

from integration.run_manifest import begin_run, finish_run


def test_failed_run_keeps_logs_and_atomic_final_status(tmp_path: Path) -> None:
    context = begin_run(
        tmp_path,
        {
            "git_commit": "05281a8",
            "profile": "qwen3vl-2b-int4",
            "dataset_sha256": "a" * 64,
            "seed": 20260804,
        },
    )
    (context.logs_dir / "qwen_server.log").write_text("startup failed", encoding="utf-8")
    finish_run(context, "FAILED", "qwen_not_ready")

    manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["failure_reason"] == "qwen_not_ready"
    assert (context.logs_dir / "qwen_server.log").exists()
    assert not context.manifest_path.with_suffix(".json.tmp").exists()
```

- [ ] **Step 2: Run the manifest test and verify the module is missing**

Run: `python -m pytest integration/tests/test_run_manifest.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: integration.run_manifest`.

- [ ] **Step 3: Implement an atomic run lifecycle**

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class RunContext:
    run_id: str
    root: Path
    manifest_path: Path
    metrics_dir: Path
    logs_dir: Path
    media_dir: Path


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def begin_run(output_root: Path, metadata: dict[str, object]) -> RunContext:
    now = datetime.now(timezone.utc)
    run_id = f"{now:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    root = output_root / "runs" / run_id
    context = RunContext(run_id, root, root / "run_manifest.json", root / "metrics", root / "logs", root / "media")
    for directory in (context.metrics_dir, context.logs_dir, context.media_dir):
        directory.mkdir(parents=True, exist_ok=False)
    _write_atomic(context.manifest_path, {**metadata, "run_id": run_id, "started_at": now.isoformat(), "status": "RUNNING", "failure_reason": None})
    return context


def finish_run(context: RunContext, status: str, failure_reason: str | None) -> None:
    payload = json.loads(context.manifest_path.read_text(encoding="utf-8"))
    payload.update(status=status, failure_reason=failure_reason, finished_at=datetime.now(timezone.utc).isoformat())
    _write_atomic(context.manifest_path, payload)
```

- [ ] **Step 4: Write the exact percentile and early-stop tests**

```python
from tools.four_modal_metrics import evaluate_official_gates, summarize_latency


def test_latency_summary_has_required_percentiles() -> None:
    result = summarize_latency([10.0, 20.0, 30.0, 40.0, 50.0])
    assert set(result) == {"count", "mean", "p50", "p95", "p99", "max"}
    assert result["p50"] == 30.0
    assert result["max"] == 50.0


def test_over_300ms_stops_before_accuracy() -> None:
    gate = evaluate_official_gates({"end_to_end_ms": {"p95": 301.0}})
    assert gate == {
        "status": "EARLY_STOP",
        "reason": "end_to_end_p95_over_300ms",
        "run_accuracy": False,
        "run_stability": False,
    }
```

- [ ] **Step 5: Implement one percentile function and one gate function**

```python
def summarize_latency(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("latency sample list is empty")
    percentile = lambda q: ordered[min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1)]
    return {
        "count": len(ordered),
        "mean": statistics.fmean(ordered),
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "max": ordered[-1],
    }


def evaluate_official_gates(metrics: dict[str, object]) -> dict[str, object]:
    p95 = float(metrics["end_to_end_ms"]["p95"])
    if p95 > 300.0:
        return {"status": "EARLY_STOP", "reason": "end_to_end_p95_over_300ms", "run_accuracy": False, "run_stability": False}
    return {"status": "CONTINUE", "reason": None, "run_accuracy": True, "run_stability": p95 <= 150.0}
```

- [ ] **Step 6: Port the 3B branch's remote backend and staged timing without its defaults**

Use `git diff carla_driving_rstar..team/8.4-xky-3B -- tools/run_four_modal_full_chain.py tools/four_modal_metrics.py` as the source review. Change the evaluator CLI to this exact mutually exclusive interface:

```python
backend = parser.add_mutually_exclusive_group(required=True)
backend.add_argument("--model-path", type=Path)
backend.add_argument("--qwen-base-url")
parser.add_argument("--profile", default="qwen3vl-2b-int4")
parser.add_argument("--asr-manifest", type=Path, required=True)
parser.add_argument("--multimodal-cases", type=Path, required=True)
parser.add_argument("--latency-manifest", type=Path, required=True)
parser.add_argument("--warmup", type=int, default=5)
parser.add_argument("--measured", type=int, default=10)
```

Do not require the absent synthetic `audio_ref` files declared by the historical 320-case set. Use the datasets for separate claims:

- ASR accuracy: `voice_group/test_samples/manifest.json` plus its real MP3 files.
- Multimodal action/target contract accuracy: `artifacts/four_modal_0728/stress_set/cases_v2.jsonl`, using its frozen transcript, RGB, LiDAR, vehicle, and safety data.
- End-to-end latency: `datasets/repro/full_chain_latency_v1.json`, pairing ten existing MP3s with ten distinct frozen frames.

The latency manifest contains these exact audio/frame pairs and expected ASR intents:

```python
LATENCY_PAIRS = (
    ("voice_group/test_samples/mandarin/0003.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_center__baseline.png", "SET_SPEED"),
    ("voice_group/test_samples/mandarin/0004.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_center__detector_bbox_shift.png", "EMERGENCY_STOP"),
    ("voice_group/test_samples/mandarin/0006.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_center__detector_false_positive.png", "AVOID_OBSTACLE"),
    ("voice_group/test_samples/mandarin/0008.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_center__detector_miss.png", "STOP"),
    ("voice_group/test_samples/dialect/dongbei/0081.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_center__exposure_high.png", "SET_SPEED"),
    ("voice_group/test_samples/dialect/dongbei/0075.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_center__exposure_low.png", "AVOID_OBSTACLE"),
    ("voice_group/test_samples/dialect/shaanxi/0006.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_center__motion_blur.png", "AVOID_OBSTACLE"),
    ("voice_group/test_samples/dialect/yueyu/0011.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_center__partial_occlusion.png", "EMERGENCY_STOP"),
    ("voice_group/test_samples/dialect/taiwan/0009.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_second__baseline.png", "AVOID_OBSTACLE"),
    ("voice_group/test_samples/dialect/taiwan/0081.mp3", "artifacts/four_modal_0728/stress_set/images/town03opt_multi_target_seed_20_second__detector_bbox_shift.png", "SET_SPEED"),
)
```

Store those rows as JSON, add source SHA256 at freeze time, and add a unit test that all 20 referenced files exist, hashes match, and all ten frame hashes are unique.

Create the remote backend with `resolve_qwen_profile(args.profile)` and record these exact stage keys for every row:

```python
    stage_timing = {
    "asr_ms": asr_finished_ms - audio_ready_ms,
    "instruction_parse_ms": nlu_finished_ms - asr_finished_ms,
    "asr_nlu_ms": nlu_finished_ms - audio_ready_ms,
    "sensor_fusion_ready_ms": fusion_ready_ms - nlu_finished_ms,
    "qwen_service_ms": qwen_finished_ms - qwen_started_ms,
    "post_qwen_control_ms": control_ready_ms - qwen_finished_ms,
    "end_to_end_ms": control_ready_ms - audio_ready_ms,
}
```

Do not reuse one image for all measured requests: load the frame path recorded by each frozen sample and include `frame_sha256` in raw JSONL.

- [ ] **Step 7: Test the remote evaluator with a fake OpenAI-compatible backend**

The fake response body must match the existing one-token constrained endpoint:

```python
{
    "choices": [{
        "message": {"content": "B"},
        "logprobs": {"content": [{"token": "B", "logprob": -0.01}]},
    }]
}
```

Run: `python -m pytest integration/tests/test_run_manifest.py integration/tests/test_four_modal_full_chain_remote.py integration/tests/test_qwen_four_modal_stress_set.py -q`

Expected: PASS; the raw file has five warm-ups excluded from statistics, ten measured dynamic-frame records, all seven timing keys, and an independently checkable `instruction_parse_ms` P95.

- [ ] **Step 8: Commit the evidence contract**

```powershell
git add integration/run_manifest.py integration/tests/test_run_manifest.py tools/four_modal_metrics.py tools/run_four_modal_full_chain.py integration/tests/test_four_modal_full_chain_remote.py integration/tests/test_qwen_four_modal_stress_set.py datasets/repro/full_chain_latency_v1.json
git commit -m "feat: standardize full-chain evidence and gates"
```

### Task 5: Build and Prove the Portable CUDA 13.2 vLLM Kernel Wheel

**Files:**
- Create: `third_party/vllm.lock.json`
- Create: `docker/Dockerfile.vllm-builder-cu132`
- Create: `docker/patches/vllm-cu132-torch.patch`
- Create: `docker/requirements-cu132-build.txt`
- Create: `tools/verify_qwen_kernel.py`
- Create: `integration/tests/test_vllm_cu132_build.py`
- Create outside Git: `release_assets/source/vllm-568afb3a13806beb53bb2e6bd518269357b237c0.tar.gz`
- Create outside Git: `release_assets/wheelhouse/vllm-0.26.1.dev0+g568afb3a1.d20260802-*.whl`

**Interfaces:**
- Consumes: clean vLLM commit `568afb3a13806beb53bb2e6bd518269357b237c0`, CUDA 13.2 developer image, and a wheelhouse containing `torch==2.12.1+cu132`.
- Produces: an offline vLLM wheel compiled with `TORCH_CUDA_ARCH_LIST="8.0;12.0+PTX"`, plus `verify_kernel_log(path: Path) -> dict[str, str]` that rejects a non-GPTQ or non-Marlin INT4 launch.

- [ ] **Step 1: Write failing build-lock and kernel-evidence tests**

```python
from pathlib import Path

import pytest

from tools.verify_qwen_kernel import verify_kernel_log


ROOT = Path(__file__).resolve().parents[2]


def test_vllm_builder_targets_a800_and_rtx5070() -> None:
    text = (ROOT / "docker/Dockerfile.vllm-builder-cu132").read_text(encoding="utf-8")
    assert "nvidia/cuda:13.2.0-devel-ubuntu24.04" in text
    assert 'TORCH_CUDA_ARCH_LIST="8.0;12.0+PTX"' in text
    assert "568afb3a13806beb53bb2e6bd518269357b237c0" in text


def test_kernel_log_requires_real_marlin_selection(tmp_path: Path) -> None:
    invalid = tmp_path / "server.log"
    invalid.write_text("quantization=auto_gptq\nUsing ExllamaLinearKernel\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Marlin"):
        verify_kernel_log(invalid)

    valid = tmp_path / "marlin.log"
    valid.write_text(
        "quantization=auto_gptq\nUsing MarlinLinearKernel for AutoGPTQLinearMethod\n",
        encoding="utf-8",
    )
    evidence = verify_kernel_log(valid)
    assert evidence["quantization"] == "auto_gptq"
    assert evidence["linear_kernel"] == "MarlinLinearKernel"
```

- [ ] **Step 2: Run the tests and confirm builder/verifier files are missing**

Run: `python -m pytest integration/tests/test_vllm_cu132_build.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: tools.verify_qwen_kernel`.

- [ ] **Step 3: Pin the exact upstream source**

Create `third_party/vllm.lock.json`:

```json
{
  "repository": "https://github.com/vllm-project/vllm.git",
  "commit": "568afb3a13806beb53bb2e6bd518269357b237c0",
  "expected_version": "0.26.1.dev0+g568afb3a1.d20260802",
  "torch": "2.12.1+cu132",
  "cuda": "13.2",
  "cuda_arch_list": "8.0;12.0+PTX"
}
```

Export that clean commit, not the modified WSL working tree:

```powershell
wsl git -C /home/restar/src/vllm-v0.26.0-cu132 archive --format=tar.gz --output=/mnt/f/carla_driving_rstar/release_assets/source/vllm-568afb3a13806beb53bb2e6bd518269357b237c0.tar.gz 568afb3a13806beb53bb2e6bd518269357b237c0
```

- [ ] **Step 4: Add the minimal CUDA 13.2 torch compatibility patch**

`docker/patches/vllm-cu132-torch.patch` contains only this dependency-pin change; it does not change vLLM kernels, scheduler behavior, or model code:

```diff
diff --git a/pyproject.toml b/pyproject.toml
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -7,7 +7,6 @@ requires = [
     "setuptools>=77.0.3,<81.0.0",
     "setuptools-scm>=8.0",
     "setuptools-rust>=1.9.0",
-    "torch == 2.11.0",
     "wheel",
     "jinja2",
 ]
diff --git a/requirements/build/cuda.txt b/requirements/build/cuda.txt
--- a/requirements/build/cuda.txt
+++ b/requirements/build/cuda.txt
@@ -5,7 +5,6 @@ packaging>=24.2
 setuptools>=77.0.3,<81.0.0
 setuptools-scm>=8
 setuptools-rust>=1.9.0
-torch==2.11.0
 wheel
 jinja2>=3.1.6
 regex
diff --git a/requirements/cuda.txt b/requirements/cuda.txt
--- a/requirements/cuda.txt
+++ b/requirements/cuda.txt
@@ -4,11 +4,6 @@
 numba == 0.65.0 # Required for N-gram speculative decoding

 # Dependencies for NVIDIA GPUs
-torch==2.11.0
-torchaudio==2.11.0
-# These must be updated alongside torch
-torchvision==0.26.0
-torchcodec >= 0.14
 PyNvVideoCodec==2.0.4
```

The builder supplies `torch==2.12.1+cu132` from the offline build wheelhouse.

- [ ] **Step 5: Implement the reproducible wheel builder**

```dockerfile
FROM nvidia/cuda:13.2.0-devel-ubuntu24.04@sha256:f9492f2eea77fbc3d0c14fa8738f35946b42da72917bf5959d284ca39b4f209a AS build
ENV DEBIAN_FRONTEND=noninteractive CUDA_HOME=/usr/local/cuda-13.2 \
    TORCH_CUDA_ARCH_LIST="8.0;12.0+PTX" MAX_JOBS=4 NVCC_THREADS=2 \
    VLLM_TARGET_DEVICE=cuda VLLM_USE_PRECOMPILED=0 \
    SETUPTOOLS_SCM_PRETEND_VERSION_FOR_VLLM=0.26.1.dev0+g568afb3a1.d20260802
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-dev python3-pip git patch ninja-build cmake && rm -rf /var/lib/apt/lists/*
WORKDIR /src/vllm
ADD release_assets/source/vllm-568afb3a13806beb53bb2e6bd518269357b237c0.tar.gz /src/vllm
COPY docker/patches/vllm-cu132-torch.patch /tmp/vllm-cu132-torch.patch
COPY docker/requirements-cu132-build.txt /src/vllm/docker/requirements-cu132-build.txt
COPY release_assets/wheelhouse-build/ /wheelhouse-build/
RUN patch -p1 < /tmp/vllm-cu132-torch.patch
RUN python3 -m pip install --break-system-packages --no-index --find-links=/wheelhouse-build -r /src/vllm/docker/requirements-cu132-build.txt
RUN python3 -m build --wheel --no-isolation --outdir /out

FROM scratch AS export
COPY --from=build /out/ /
```

Pin every line in `docker/requirements-cu132-build.txt`: `torch==2.12.1+cu132`, `setuptools==78.1.0`, `setuptools-scm==10.2.1`, `setuptools-rust==1.13.0`, `wheel==0.47.0`, `cmake==4.4.0`, `ninja==1.13.0`, `packaging==26.2`, `jinja2==3.1.6`, `regex==2026.7.19`, `protobuf==6.33.6`, and `build==1.5.0`. These are the versions from the already working local CUDA 13.2 build environment.

- [ ] **Step 6: Download the pinned build wheels once and preserve their hashes**

Run:

```powershell
py -3.12 -m pip download --dest release_assets/wheelhouse-build --platform manylinux_2_28_x86_64 --python-version 312 --implementation cp --abi cp312 --only-binary=:all: --index-url https://download.pytorch.org/whl/cu132 "torch==2.12.1+cu132"
py -3.12 -m pip download --dest release_assets/wheelhouse-build --platform manylinux_2_28_x86_64 --python-version 312 --implementation cp --abi cp312 --only-binary=:all: "setuptools==78.1.0" "setuptools-scm==10.2.1" "setuptools-rust==1.13.0" "wheel==0.47.0" "cmake==4.4.0" "ninja==1.13.0" "packaging==26.2" "jinja2==3.1.6" "regex==2026.7.19" "protobuf==6.33.6" "build==1.5.0"
py -3.12 tools/generate_model_manifest.py release_assets/wheelhouse-build --model-name vllm-cu132-build-wheelhouse --license mixed-open-source-build-dependencies --output release_assets/wheelhouse-build.manifest.json
```

Expected: all build wheels are local and the generated manifest records each filename, byte size, SHA256, and aggregate hash. The release builder later includes this manifest as build provenance, not as an A800 runtime dependency.

- [ ] **Step 7: Build the wheel once on the development machine**

Run:

```powershell
docker build --target export --output type=local,dest=release_assets/wheelhouse -f docker/Dockerfile.vllm-builder-cu132 .
```

Expected: exactly one CPython 3.12 `vllm-0.26.1.dev0+g568afb3a1.d20260802-*.whl` is emitted and `unzip -l` shows CUDA extension objects; the build log records both `compute_80` and `compute_120`/PTX compilation targets.

- [ ] **Step 8: Implement strict kernel-log verification**

```python
def verify_kernel_log(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "quantization=auto_gptq" not in text:
        raise ValueError("Qwen launch did not prove auto_gptq quantization")
    if "Using MarlinLinearKernel" not in text:
        raise ValueError("Qwen launch did not select MarlinLinearKernel")
    mode = "gemv" if "gemv" in text.lower() else "marlin_batch1"
    return {"quantization": "auto_gptq", "linear_kernel": "MarlinLinearKernel", "batch1_path": mode}
```

The verifier reports `gemv` only if the runtime log/profiler actually contains that token; otherwise it reports the proven Marlin batch-1 path. Do not label an unobserved GEMV kernel as enabled.

- [ ] **Step 9: Run the builder/verifier tests**

Run: `python -m pytest integration/tests/test_vllm_cu132_build.py -q`

Expected: PASS; source lock, dual architecture list, CUDA 13.2 builder, and strict Marlin evidence are all enforced.

- [ ] **Step 10: Commit recipes and verifier, not the generated wheel/source archive**

```powershell
git add third_party/vllm.lock.json docker/Dockerfile.vllm-builder-cu132 docker/patches/vllm-cu132-torch.patch docker/requirements-cu132-build.txt tools/verify_qwen_kernel.py integration/tests/test_vllm_cu132_build.py
git commit -m "build: pin portable CUDA 13.2 vLLM wheel"
```

### Task 6: Build the CUDA 13.2 Three-Service Offline Stack

**Files:**
- Modify: `docker/Dockerfile.controller`
- Create: `docker/Dockerfile.qwen-cu132`
- Create: `docker/entrypoints/qwen.sh`
- Modify: `docker/entrypoints/controller.sh`
- Create: `docker/requirements-qwen.txt`
- Create: `tools/verify_model_manifest.py`
- Modify: `docker/compose.yaml`
- Create: `config/repro/common.env`
- Create: `config/repro/rtx5070.env`
- Create: `config/repro/a800-safe.env`
- Create: `config/repro/a800-optimized.env`
- Create: `integration/tests/test_repro_compose.py`
- Create: `integration/tests/test_model_manifest.py`

**Interfaces:**
- Consumes: staged CPython 3.12 `release_assets/wheelhouse/vllm-0.26.1.dev0+g568afb3a1.d20260802-*.whl`, `release_assets/weights/qwen3vl-2b-int4/`, `weights/model_manifest.json`, and controller source.
- Produces: healthy services `carla`, `qwen`, and `controller`; Qwen endpoint `http://qwen:8001/v1`; persistent output at `/output/runs` only.

- [ ] **Step 1: Write a failing static Compose boundary test**

```python
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
```

- [ ] **Step 2: Run the static test and confirm the current two-service/development-mount failure**

Run: `python -m pytest integration/tests/test_repro_compose.py -q`

Expected: FAIL during collection because `tools.verify_model_manifest` is absent; after adding only that module, the Compose assertion still fails because the current file lacks `qwen` and mounts `../artifacts`.

- [ ] **Step 3: Implement strict per-profile manifest verification**

```python
def verify_profile(manifest_path: Path, root: Path, profile: str) -> dict[str, object]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [item for item in payload["models"] if item["profile"] == profile]
    if len(matches) != 1:
        raise ValueError(f"manifest must contain one profile entry: {profile}")
    entry = matches[0]
    expected = {item["path"]: item for item in entry["files"]}
    actual = {str(path.relative_to(root)).replace("\\", "/"): path for path in root.rglob("*") if path.is_file()}
    if set(actual) != set(expected):
        raise ValueError("model file set does not match manifest")
    for relative, path in actual.items():
        metadata = expected[relative]
        if path.stat().st_size != metadata["bytes"]:
            raise ValueError(f"byte size mismatch: {relative}")
        if sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"SHA256 mismatch: {relative}")
    return entry
```

The CLI requires `--manifest`, `--root`, and `--profile`, prints the verified revision/quantization/kernel fields, and exits nonzero on path traversal, duplicate entries, file-set mismatch, byte mismatch, or SHA256 mismatch.

- [ ] **Step 4: Pin controller userspace to CUDA 13.2 and copy all runtime assets**

Start `docker/Dockerfile.controller` with:

```dockerfile
FROM nvidia/cuda:13.2.0-cudnn-runtime-ubuntu24.04@sha256:7a31e9bfb2086e4b1ac08aa8e4718d7860730ecc6a9882d2f1e5ed6239f8ef5b
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3 python3-pip python3-venv libsndfile1 portaudio19-dev libglib2.0-0 libgl1 ffmpeg curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY docker/requirements-controller.txt docker/requirements-voice.txt /tmp/requirements/
COPY release_assets/wheelhouse-controller/ /wheelhouse-controller/
RUN python3 -m pip install --break-system-packages --no-index --find-links=/wheelhouse-controller -r /tmp/requirements/requirements-controller.txt -r /tmp/requirements/requirements-voice.txt
COPY . /app
COPY release_assets/weights/asr/SenseVoiceSmall /models/asr/SenseVoiceSmall
COPY weights/model_manifest.json /models/model_manifest.json
ADD release_assets/source/scenario_runner-94ff3b8af752bad2b9d464ad5105868906aa34c0.tar.gz /opt/scenario_runner
COPY release_assets/package/datasets/ /app/release_data/datasets/
COPY release_assets/package/scenarios/ /app/release_data/scenarios/
COPY release_assets/package/samples/ /app/release_data/samples/
ENV SCENARIO_RUNNER_ROOT=/opt/scenario_runner PYTHONPATH=/opt/scenario_runner:/app REPRO_DATA_ROOT=/app/release_data
ENTRYPOINT ["/app/docker/entrypoints/controller.sh"]
```

The implementation must keep dependencies pinned with `==` in both requirement files and must set the ASR model path to `/models/asr/SenseVoiceSmall` and the active LoRA path to `/app/voice_group/lora_dialect` through Compose. Before `exec`, `controller.sh` calls `verify_model_manifest.py` once with `--profile sensevoice-small --root /models/asr/SenseVoiceSmall` and once with `--profile sensevoice-dialect-lora --root /app/voice_group/lora_dialect`.

Prepare the embedded ScenarioRunner source once before building the controller image:

```powershell
./scripts/fetch_scenario_runner.ps1 -Target release_assets/source/scenario_runner-worktree
git -C release_assets/source/scenario_runner-worktree archive --format=tar.gz --output=../scenario_runner-94ff3b8af752bad2b9d464ad5105868906aa34c0.tar.gz 94ff3b8af752bad2b9d464ad5105868906aa34c0
```

Hash the archive into the release build-provenance manifest; neither the controller entrypoint nor the A800 contacts GitHub.

- [ ] **Step 5: Create the Qwen runtime image from a prebuilt CUDA 13.2 wheel**

```dockerfile
FROM nvidia/cuda:13.2.0-cudnn-runtime-ubuntu24.04@sha256:7a31e9bfb2086e4b1ac08aa8e4718d7860730ecc6a9882d2f1e5ed6239f8ef5b
ENV DEBIAN_FRONTEND=noninteractive HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3 python3-pip curl libnuma1 && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/qwen
COPY release_assets/wheelhouse/ /wheelhouse/
COPY docker/requirements-qwen.txt /tmp/requirements-qwen.txt
RUN python3 -m pip install --break-system-packages --no-index --find-links=/wheelhouse -r /tmp/requirements-qwen.txt
COPY release_assets/weights/qwen3vl-2b-int4/ /models/qwen/
COPY weights/model_manifest.json /models/model_manifest.json
COPY tools/verify_model_manifest.py /app/tools/verify_model_manifest.py
COPY docker/entrypoints/qwen.sh /usr/local/bin/qwen-entrypoint
RUN chmod 0555 /usr/local/bin/qwen-entrypoint
EXPOSE 8001
ENTRYPOINT ["/usr/local/bin/qwen-entrypoint"]
```

The wheel used here is built before release with `TORCH_CUDA_ARCH_LIST="8.0;12.0+PTX"` so one image supports A800 SM80 and RTX 5070 SM120. Store the wheel SHA256 in `weights/model_manifest.json`; the A800 never builds it.

- [ ] **Step 6: Freeze the complete Linux CPython 3.12 runtime wheelhouse**

Create `docker/requirements-qwen.txt` with these direct pins:

```text
torch==2.12.1+cu132
torchvision==0.27.1+cu132
vllm==0.26.1.dev0+g568afb3a1.d20260802
transformers==5.14.1
openai==2.52.0
pillow==12.2.0
```

Then download every transitive Linux wheel beside the locally built vLLM wheel and hash the finished directory:

```powershell
py -3.12 -m pip download --dest release_assets/wheelhouse --find-links release_assets/wheelhouse --extra-index-url https://download.pytorch.org/whl/cu132 --platform manylinux_2_28_x86_64 --python-version 312 --implementation cp --abi cp312 --only-binary=:all: -r docker/requirements-qwen.txt
py -3.12 tools/generate_model_manifest.py release_assets/wheelhouse --model-name qwen-vllm-cu132-runtime-wheelhouse --license mixed-open-source-runtime-dependencies --output release_assets/wheelhouse.manifest.json
```

Expected: every requirement resolves from local wheels during a dry-run install with `--no-index`; the manifest fixes the actual transitive versions and hashes included in the image build.

Replace the controller requirement ranges with these tested direct pins:

```text
# docker/requirements-controller.txt
carla==0.9.16
numpy==2.2.6
onnxruntime==1.22.1
pillow==12.2.0
pygame==2.6.1
pytest==9.0.3

# docker/requirements-voice.txt
torch==2.12.1+cu132
torchaudio==2.12.1+cu132
soundfile==0.14.0
funasr==1.3.22
modelscope==1.38.1
peft==0.19.1
openpyxl==3.1.5
openai==2.52.0
safetensors==0.7.0
faster-whisper==1.2.1
opencc-python-reimplemented==0.1.7
jupyter==1.1.1
nbconvert==7.16.6
nbformat==5.10.4
```

Download the Linux CPython 3.12 controller/voice wheelhouse with the same `manylinux_2_28_x86_64`, `cp312`, and CUDA 13.2 index flags used above, then generate `release_assets/wheelhouse-controller.manifest.json`. Before building the image, perform a disposable `python:3.12` container install using only that wheelhouse; fail if any package requests the network or falls back to an sdist.

- [ ] **Step 7: Validate weights/revision and start vLLM in the entrypoint**

```bash
#!/usr/bin/env bash
set -euo pipefail
python3 /app/tools/verify_model_manifest.py --manifest /models/model_manifest.json --profile qwen3vl-2b-int4 --root /models/qwen
exec vllm serve /models/qwen \
  --served-model-name "${QWEN_SERVED_MODEL:-qwen3vl-2b-int4}" \
  --host 0.0.0.0 --port 8001 \
  --max-model-len "${QWEN_MAX_MODEL_LEN:-1024}" \
  --gpu-memory-utilization "${QWEN_GPU_MEMORY_UTILIZATION:-0.72}" \
  --limit-mm-per-prompt image=1 \
  ${QWEN_EXTRA_ARGS:-}
```

Copy `tools/verify_model_manifest.py` into the image at `/app/tools/verify_model_manifest.py`; do not silence verification failures.

- [ ] **Step 8: Replace Compose with pinned images, health checks, and one output mount**

Use images `carla-simulator:0.9.16`, `carla-controller:${RELEASE_COMMIT}`, and `qwen-vllm-cu132:${QWEN_PROFILE}`. Mount only `${OUTPUT_DIR:-./output}:/output`; all datasets, scenarios, ASR assets, Qwen weights, and code remain inside images. Set `gpus: all`, `ipc: host`, health-check Qwen via `/v1/models`, and make controller depend on healthy CARLA and Qwen.

- [ ] **Step 9: Add exact hardware profiles**

`config/repro/rtx5070.env`:

```dotenv
QWEN_PROFILE=qwen3vl-2b-int4
QWEN_GPU_MEMORY_UTILIZATION=0.72
QWEN_MAX_MODEL_LEN=1024
QWEN_EXTRA_ARGS=--attention-backend TRITON_ATTN --mm-encoder-attn-backend TORCH_SDPA -cc.cudagraph_mode=NONE
CARLA_QUALITY_LEVEL=Low
CARLA_RESOLUTION=640x360
```

`config/repro/a800-safe.env` uses `0.60`, max length `2048`, and `--enforce-eager --attention-backend TRITON_ATTN --mm-encoder-attn-backend TORCH_SDPA`. `config/repro/a800-optimized.env` uses `0.75`, max length `2048`, and `--enable-prefix-caching`, allowing vLLM's stable CUDA Graph/attention selection. Both retain `qwen3vl-2b-int4`, a 256×256 montage, and a 64-token visual budget. The checkpoint declares GPTQ; vLLM chooses the compatible implementation, and preflight accepts the optimized INT4 route only after `verify_qwen_kernel.py` proves `MarlinLinearKernel` in the real startup log. The run manifest records requested and actual attention backends plus CUDA Graph mode.

- [ ] **Step 10: Verify configuration and shell syntax without building images**

Run: `python -m pytest integration/tests/test_repro_compose.py integration/tests/test_model_manifest.py -q`

Run: `wsl bash -n docker/entrypoints/qwen.sh docker/entrypoints/controller.sh`

Run: `docker compose --env-file config/repro/rtx5070.env -f docker/compose.yaml config --quiet`

Expected: all three commands exit 0; rendered Compose contains no host model/cache/development mount.

- [ ] **Step 11: Commit the offline stack definition**

```powershell
git add docker/Dockerfile.controller docker/Dockerfile.qwen-cu132 docker/entrypoints/qwen.sh docker/entrypoints/controller.sh docker/requirements-controller.txt docker/requirements-voice.txt docker/requirements-qwen.txt docker/compose.yaml config/repro integration/tests/test_repro_compose.py integration/tests/test_model_manifest.py tools/verify_model_manifest.py
git commit -m "feat: define CUDA 13.2 offline runtime stack"
```

### Task 7: Implement One-Click Preflight, Smoke, Evaluate, Demo, and Stability Modes

**Files:**
- Create: `tools/repro_cli.py`
- Create: `integration/tests/test_repro_cli.py`
- Create: `run.sh`
- Create: `stop.sh`
- Create: `run.ps1`
- Create: `stop.ps1`

**Interfaces:**
- Consumes: `begin_run`, `finish_run`, `evaluate_official_gates`, Compose profiles, `/app/release_data`, and `/output/runs` inside the controller image.
- Produces: container CLI `python3 -m tools.repro_cli {preflight,smoke,evaluate,demo,stability} --data-root /app/release_data --output-root /output`, `output/latest_run_id.txt`, and host wrappers that require Docker but no host Python/venv.

- [ ] **Step 1: Write failing command-order and early-stop tests**

```python
from tools.repro_cli import EvaluationDecision, build_evaluation_steps, parse_args


def test_evaluate_orders_latency_before_accuracy() -> None:
    assert build_evaluation_steps() == ["preflight", "warmup", "latency_gate", "accuracy", "scenarios"]


def test_early_stop_removes_expensive_steps() -> None:
    decision = EvaluationDecision.from_latency_p95(481.41)
    assert decision.status == "EARLY_STOP"
    assert decision.remaining_steps == []


def test_stability_is_never_implicit() -> None:
    args = parse_args(["evaluate", "--profile", "rtx5070"])
    assert args.mode == "evaluate"
    assert "stability" not in build_evaluation_steps()


def test_frozen_physical_scenario_selection() -> None:
    assert SMOKE_AUDIO_SOURCE == "voice_group/test_samples/dialect/dongbei/0081.mp3"
    assert SMOKE_AUDIO_RUNTIME == "samples/audio/smoke_set_speed_20.wav"
    assert SCENARIO_SETS["smoke"] == ("scenarios/smoke/S01_set_speed_20.json",)
    assert SCENARIO_SETS["evaluate"] == (
        "scenarios/smoke/S01_set_speed_20.json",
        "scenarios/regression/REG_008_challenge_pedestrian.json",
        "scenarios/safety_D/D07_low_ttc_emergency_brake.json",
    )
```

- [ ] **Step 2: Run the CLI tests and verify the module is absent**

Run: `python -m pytest integration/tests/test_repro_cli.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: tools.repro_cli`.

- [ ] **Step 3: Implement explicit modes and evaluation decisions**

```python
@dataclass(frozen=True, slots=True)
class EvaluationDecision:
    status: str
    remaining_steps: list[str]

    @classmethod
    def from_latency_p95(cls, latency_p95_ms: float) -> "EvaluationDecision":
        if latency_p95_ms > 300.0:
            return cls("EARLY_STOP", [])
        return cls("CONTINUE", ["accuracy", "scenarios"])


def build_evaluation_steps() -> list[str]:
    return ["preflight", "warmup", "latency_gate", "accuracy", "scenarios"]


SCENARIO_SETS = {
    "smoke": ("scenarios/smoke/S01_set_speed_20.json",),
    "evaluate": (
        "scenarios/smoke/S01_set_speed_20.json",
        "scenarios/regression/REG_008_challenge_pedestrian.json",
        "scenarios/safety_D/D07_low_ttc_emergency_brake.json",
    ),
}

SMOKE_AUDIO_SOURCE = "voice_group/test_samples/dialect/dongbei/0081.mp3"
SMOKE_AUDIO_RUNTIME = "samples/audio/smoke_set_speed_20.wav"
```

The Bash/PowerShell wrapper checks Docker Engine, Compose, NVIDIA runtime, disk free space, and all three image digests. The container CLI checks GPU name/memory/driver, CUDA 13.2, Qwen/ASR/kernel manifests, Git commit, and dataset hash. Together they write `environment.json` even when preflight fails.

`smoke` runs the frozen 16 kHz mono PCM WAV derived from Dongbei-dialect `0081.mp3` (SET_SPEED 20) and `S01_set_speed_20`. `evaluate` runs 5 warm-ups, 10 dynamic-frame latency samples, then frozen accuracy and the named basic/obstacle/emergency scenarios only if P95 is `<= 300 ms`. `demo` records one physical CARLA run. `stability` runs 30 minutes only when invoked explicitly and refuses to start unless an existing evaluate manifest has end-to-end P95 `<= 150 ms`.

Immediately after `begin_run`, atomically write the run ID plus newline to `output/latest_run_id.txt`. This pointer is convenience metadata only; promotion still verifies the selected run's manifest and hashes.

- [ ] **Step 4: Add a subprocess seam so unit tests never start Docker**

```python
CommandRunner = Callable[[list[str], Path | None], subprocess.CompletedProcess[str]]


def run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
```

Pass `runner: CommandRunner = run_command` into `run_preflight`, `run_smoke`, `run_evaluate`, `run_demo`, and `run_stability`. On any nonzero result, call `finish_run(..., "FAILED", exact_reason)` before returning the child exit code.

- [ ] **Step 5: Create host wrappers that orchestrate Docker without host Python**

`run.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:?usage: ./run.sh MODE --profile PROFILE}"
shift
profile="rtx5070"
if [[ "${1:-}" == "--profile" ]]; then
  profile="${2:?--profile requires a value}"
  shift 2
fi
case "$profile" in
  rtx5070|a800-safe|a800-optimized) ;;
  *) echo "unsupported profile: $profile" >&2; exit 2 ;;
esac
env_file="$repo_dir/config/$profile.env"
compose_file="$repo_dir/docker-compose.yml"
[[ -f "$compose_file" ]] || compose_file="$repo_dir/docker/compose.yaml"
compose=(docker compose --env-file "$env_file" -f "$compose_file")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --wait carla qwen
mkdir -p "$repo_dir/output/bootstrap"
"${compose[@]}" logs --no-color qwen > "$repo_dir/output/bootstrap/qwen.log"
"${compose[@]}" logs --no-color carla > "$repo_dir/output/bootstrap/carla.log"
exec "${compose[@]}" run --rm controller \
  python3 -m tools.repro_cli "$mode" \
  --data-root /app/release_data --output-root /output \
  --qwen-log /output/bootstrap/qwen.log --carla-log /output/bootstrap/carla.log "$@"
```

`stop.sh` computes the same release root, chooses the profile from `REPRO_PROFILE` with default `rtx5070`, and runs `docker compose ... down` without `--volumes`, preserving `/output`. PowerShell wrappers implement the same `docker compose config/up/logs/run/down` sequence directly; they do not invoke `py`, `python`, a repository venv, or WSL. All wrappers propagate the exact Docker/controller exit code. The container preflight passes `qwen.log` to `verify_qwen_kernel.py`, copies both bootstrap logs into the run log directory, and records actual attention/CUDA Graph/Marlin evidence in `environment.json`.

- [ ] **Step 6: Run focused CLI and syntax tests**

Run: `python -m pytest integration/tests/test_repro_cli.py -q`

Run: `wsl bash -n run.sh stop.sh`

Expected: PASS and shell syntax exit code 0. A static test asserts every `python3 -m tools.repro_cli` occurrence in `run.sh` is an argument to `docker compose run`, never a host command.

- [ ] **Step 7: Commit the one-click entry points**

```powershell
git add tools/repro_cli.py integration/tests/test_repro_cli.py run.sh stop.sh run.ps1 stop.ps1
git commit -m "feat: add one-click reproduction modes"
```

### Task 8: Verify Model Assets and Build a Deterministic Docker Archive

**Files:**
- Modify: `tools/verify_model_manifest.py`
- Create: `tools/build_submission_package.py`
- Create: `integration/tests/test_build_submission_package.py`
- Modify: `integration/tests/test_model_manifest.py`
- Modify: `tools/generate_model_manifest.py`
- Modify: `docker/scripts/export-images.ps1`
- Create: `docker/scripts/export-images.sh`
- Create: `weights/download_fallback.sh`
- Create: `weights/download_asr_fallback.sh`
- Create: `weights/download_optional_models.sh`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: three exact image tags, fixed Qwen/ASR assets, prebuilt vLLM wheel, Git commit, and `release_assets/` staging area.
- Produces: `dist/carla-language-control-submission/image.tar`, `dist/carla-language-control-submission/image.tar.sha256`, `weights/model_manifest.json`, `weights/SHA256SUMS`, and a release validation report.

- [ ] **Step 1: Write a failing archive-validation test using a fake Docker client**

```python
from pathlib import Path

import pytest

from tools.build_submission_package import ReleaseInputs, validate_release_inputs


def test_release_rejects_missing_primary_weight(tmp_path: Path) -> None:
    inputs = ReleaseInputs(
        root=tmp_path,
        image_tags=("carla-simulator:0.9.16", "carla-controller:05281a8", "qwen-vllm-cu132:qwen3vl-2b-int4"),
        primary_weight=tmp_path / "weights/qwen3vl-2b-int4/model.safetensors",
        vllm_wheel=tmp_path / "wheelhouse/vllm-0.26.1.dev0+g568afb3a1.d20260802-cp312-cp312-linux_x86_64.whl",
        asr_manifest=tmp_path / "voice_group/test_samples/manifest.json",
        multimodal_cases=tmp_path / "artifacts/four_modal_0728/stress_set/cases_v2.jsonl",
        latency_manifest=tmp_path / "datasets/repro/full_chain_latency_v1.json",
    )
    with pytest.raises(FileNotFoundError, match="primary model weight"):
        validate_release_inputs(inputs)
```

- [ ] **Step 2: Run the test and confirm the builder does not exist**

Run: `python -m pytest integration/tests/test_build_submission_package.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: tools.build_submission_package`.

- [ ] **Step 3: Implement strict input validation and stable file hashes**

```python
@dataclass(frozen=True, slots=True)
class ReleaseInputs:
    root: Path
    image_tags: tuple[str, str, str]
    primary_weight: Path
    vllm_wheel: Path
    asr_manifest: Path
    multimodal_cases: Path
    latency_manifest: Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_release_inputs(inputs: ReleaseInputs) -> None:
    if not inputs.primary_weight.is_file():
        raise FileNotFoundError(f"primary model weight missing: {inputs.primary_weight}")
    if not inputs.vllm_wheel.is_file():
        raise FileNotFoundError(f"prebuilt CUDA 13.2 vLLM wheel missing: {inputs.vllm_wheel}")
    for label, path in (
        ("ASR manifest", inputs.asr_manifest),
        ("multimodal contract cases", inputs.multimodal_cases),
        ("full-chain latency manifest", inputs.latency_manifest),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} missing: {path}")
    if len(set(inputs.image_tags)) != 3:
        raise ValueError("release requires three distinct image tags")
```

- [ ] **Step 4: Extend the model manifest with immutable runtime evidence**

Each model entry must contain:

```json
{
  "profile": "qwen3vl-2b-int4",
  "model_id": "h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4",
  "revision": "f91db2369bd00e7ec20bf09b6a0080cdb26aefa5",
  "checkpoint_quantization": "gptq",
  "required_linear_kernel": "MarlinLinearKernel",
  "image_max_side": 256,
  "visual_tokens": 64,
  "attention_backend": "runtime-recorded",
  "attention_backend_required_evidence": true,
  "cuda_userspace": "13.2",
  "torch_cuda_arch_list": "8.0;12.0+PTX",
  "files": []
}
```

Populate `files` with sorted relative paths, sizes, and SHA256 values. `verify_model_manifest.py` must reject an unexpected, missing, or mismatched file and must print the verified profile/revision/kernel configuration on success.

Add a second manifest entry for `iic/SenseVoiceSmall` revision `7bf452403abd7353a300cd760f7adae7701c92c1` and a third for `voice_group/lora_dialect/adapter_model.safetensors` with byte size `6922192` and SHA256 `38d541099157ba5c35d8256f2ebd8a374cae85a5ca7eb9b2a7cb8a033c624de1`. The controller preflight verifies all three entries before accepting ASR readiness.

- [ ] **Step 5: Assemble and verify frozen evaluation assets without false claims**

The builder copies these exact sources into the release:

```text
CARLA-Language-Benchmark/                         -> datasets/CARLA-Language-Benchmark/
artifacts/four_modal_0728/stress_set/cases_v2.jsonl -> datasets/frozen_validation/multimodal/cases.jsonl
artifacts/four_modal_0728/stress_set/images/      -> datasets/frozen_validation/multimodal/images/
artifacts/four_modal_0728/stress_set/lidar/       -> datasets/frozen_validation/multimodal/lidar/
voice_group/test_samples/                         -> datasets/frozen_validation/asr/
datasets/repro/full_chain_latency_v1.json         -> datasets/frozen_validation/full_chain_latency_v1.json
scenarios/                                        -> scenarios/
voice_group/test_samples/dialect/dongbei/0081.mp3 -> samples/audio/smoke_set_speed_20.wav (ffmpeg: mono, 16 kHz, PCM s16le)
artifacts/B_role_validation/local_3b_awq_0803_baseline_smoke.json -> metrics/historical_5070/raw/
artifacts/B_role_validation/qwen25_3b_awq_0803_target10_baseline.json -> metrics/historical_5070/raw/
artifacts/B_role_validation/qwen25_3b_awq_0803_target10_cuda132_triton.json -> metrics/historical_5070/raw/
artifacts/B_role_validation/qwen25_3b_awq_0803_frozen320_baseline.json -> metrics/historical_5070/raw/
artifacts/B_role_validation/qwen3vl_2b_fp8_vllm_cu132_latency_gate.json -> metrics/historical_5070/raw/
artifacts/B_role_validation/qwen3vl_2b_fp8_vllm_cu132_target10_prompt_v3.json -> metrics/historical_5070/raw/
artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_latency_gate_prompt_v3.json -> metrics/historical_5070/raw/
artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_target10_prompt_v3.json -> metrics/historical_5070/raw/
artifacts/B_role_validation/qwen3vl_2b_gptq_int4_marlin_cu132_kernel_evidence.txt -> metrics/historical_5070/raw/
```

It generates the WAV with `ffmpeg -i 0081.mp3 -ac 1 -ar 16000 -c:a pcm_s16le`, then writes `samples/commands.jsonl` with the smoke file, expected transcript `速度设为20公里。`, intent `SET_SPEED`, and speed `20`. It rejects missing audio/image/LiDAR references and writes one dataset manifest with relative path, bytes, SHA256, purpose, and claim scope. It explicitly labels the 320 multimodal set's audio provenance as unavailable/synthetic and never uses those missing audio references for ASR or end-to-end claims. It writes `metrics/historical_5070/README.md` marking the copied 3B/2B files as historical diagnostics, not official full-chain results, and does not rerun those experiments.

- [ ] **Step 6: Export exactly three images into one archive**

`docker/scripts/export-images.sh` must run:

```bash
docker image inspect carla-simulator:0.9.16 carla-controller:"${RELEASE_COMMIT}" qwen-vllm-cu132:"${QWEN_PROFILE}" >/dev/null
docker save --output "${DESTINATION}/image.tar" \
  carla-simulator:0.9.16 \
  carla-controller:"${RELEASE_COMMIT}" \
  qwen-vllm-cu132:"${QWEN_PROFILE}"
sha256sum "${DESTINATION}/image.tar" > "${DESTINATION}/image.tar.sha256"
```

Update the PowerShell script to invoke the same three `docker image inspect`/`docker save` tags and write SHA256 using `Get-FileHash`. Neither script accepts a flag that omits CARLA or Qwen.

- [ ] **Step 7: Add a network fallback that verifies the same revision and hashes**

`weights/download_fallback.sh` accepts `HF_TOKEN` only from the environment, downloads to `weights/.partial`, invokes `verify_model_manifest.py`, and atomically renames `.partial` to `qwen3vl-2b-int4`. It exits 2 with a clear message when the network is unavailable; the normal `docker load` path never calls it.

`weights/download_asr_fallback.sh` fetches exactly ModelScope revision `7bf452403abd7353a300cd760f7adae7701c92c1` into `weights/.partial-asr`, verifies the committed file hashes, and atomically renames it to `SenseVoiceSmall`. Neither fallback is called by the normal offline launch.

`weights/download_optional_models.sh` accepts only `qwen3vl-2b-fp8` or `qwen25vl-3b-bf16`, maps them to revisions `46485250d8854c0a9be4f1adbc67ca47e5bb6fa5` and `66285546d2b821cf421d4f5eb2576359d3770cd3`, downloads into a partial directory, verifies the optional manifest, and atomically promotes it. It is never invoked by the default package or 5070 smoke path.

- [ ] **Step 8: Keep large release products out of Git without hiding manifests**

Add these exact ignore rules:

```gitignore
/release_assets/
/dist/
/weights/qwen3vl-2b-int4/
/weights/.partial/
/weights/SenseVoiceSmall/
/weights/.partial-asr/
*.tar
*.tar.sha256
```

Do not ignore `weights/model_manifest.json`, `weights/SHA256SUMS`, `weights/download_fallback.sh`, `weights/download_asr_fallback.sh`, or `weights/download_optional_models.sh`.

- [ ] **Step 9: Run the builder and manifest unit tests**

Run: `python -m pytest integration/tests/test_build_submission_package.py integration/tests/test_model_manifest.py -q`

Expected: PASS for valid fixtures and explicit failures for missing/mismatched weights, wheel, image tag, or checksum.

- [ ] **Step 10: Commit archive tooling, not generated archives or weights**

```powershell
git add tools/verify_model_manifest.py tools/build_submission_package.py tools/generate_model_manifest.py docker/scripts/export-images.ps1 docker/scripts/export-images.sh weights/model_manifest.json weights/SHA256SUMS weights/download_fallback.sh weights/download_asr_fallback.sh weights/download_optional_models.sh integration/tests/test_build_submission_package.py integration/tests/test_model_manifest.py .gitignore
git commit -m "feat: build deterministic offline submission archive"
```

### Task 9: Implement Reproduction Documentation and Media Tooling

**Files:**
- Create: `README_REPRO.md`
- Create: `notebooks/reproduce.ipynb`
- Create: `integration/tests/test_reproduction_docs.py`
- Create: `submission/technical_solution.md`
- Create: `tools/render_closed_loop_video.py`
- Modify: `tools/run_qwen_carla_closed_loop.py`

**Interfaces:**
- Consumes: the run/evidence schema from Task 4 and executable modes from Task 7.
- Produces: README, notebook, technical-solution source, physical-run recorder, and deterministic renderer; Task 10 supplies real evidence and renders final PDF/video.

- [ ] **Step 1: Write failing documentation-consistency tests**

```python
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_readme_contains_exact_reproduction_contract() -> None:
    text = (ROOT / "README_REPRO.md").read_text(encoding="utf-8")
    for token in (
        "docker load -i image.tar",
        "./run.sh preflight --profile a800-safe",
        "./run.sh evaluate --profile a800-optimized",
        "/output/runs/",
        "P95 <= 150 ms",
        "RTX 5070 reference",
        "A800 formal",
    ):
        assert token in text


def test_notebook_has_no_install_or_live_inference_cells() -> None:
    notebook = json.loads((ROOT / "notebooks/reproduce.ipynb").read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )
    assert "pip install" not in source
    assert "from_pretrained" not in source
    assert "RUN_DIR" in source
```

- [ ] **Step 2: Run the tests and confirm the artifacts are absent**

Run: `python -m pytest integration/tests/test_reproduction_docs.py -q`

Expected: FAIL with `FileNotFoundError` for `README_REPRO.md`.

- [ ] **Step 3: Write the reproduction README from the executable contract**

The README must contain exactly these top-level sections: `Package Contents`, `Hardware and Software`, `Inputs`, `Outputs`, `RTX 5070 Reference Run`, `A800 Formal Run`, `Expected Results`, `Failure States`, `Model and Dataset Revisions`, and `Troubleshooting`. Commands must be copy/pasteable, list both `a800-safe` and `a800-optimized`, state that `300 ms` is only early stop, and explicitly distinguish fixed-image diagnostic latency from dynamic-frame end-to-end latency.

- [ ] **Step 4: Create an offline notebook that only reads a selected run**

The first cell sets:

```python
from pathlib import Path
import os
RUN_DIR = Path(os.environ.get("CARLA_REPRO_RUN_DIR", "../metrics/reference_5070"))
```

Subsequent cells load `run_manifest.json`, `environment.json`, `model_manifest.json`, all metrics JSON, and raw JSONL; verify hashes; display the seven-key latency table; display accuracy and scenario completion; and assert that every displayed result uses one run ID. The notebook contains no `pip install`, model download, or live GPU inference cell.

- [ ] **Step 5: Add timestamped recording data to the physical closed-loop runner**

Add CLI argument `--record-dir` and write one JSONL row per captured frame:

```python
{
    "timestamp_ns": time.monotonic_ns(),
    "frame_path": str(frame_path),
    "audio_path": str(audio_path),
    "asr_text": asr_text,
    "action_contract": action_contract,
    "vehicle_speed_mps": speed_mps,
    "scenario_status": scenario_status,
}
```

Preserve original frames and JSONL; never generate a success overlay for a failed scenario.

- [ ] **Step 6: Render a deterministic 1920x1080 demonstration video**

`tools/render_closed_loop_video.py` accepts `--run-dir`, `--output`, and `--fps 20`. It verifies monotonically increasing timestamps, overlays command/ASR/action/speed/status on each real CARLA frame, muxes the original WAV, and runs `ffprobe` to confirm H.264 video, AAC audio, duration at least 20 seconds, and nonzero streams.

- [ ] **Step 7: Write the technical-solution source with evidence fields, not invented results**

`submission/technical_solution.md` must cover architecture, dataset provenance, 2B/3B choice, INT4/Marlin and 64-token visual budget, CUDA 13.2 portability, safety boundary, evaluation definitions, A800 procedure, limitations, and the official score table from `detail_answer.md`. Its current 5070 result section reads values from `metrics/reference_5070`. A clearly separated historical-diagnostics table reads the existing 3B AWQ, 2B FP8, and 2B INT4 JSON files copied by Task 8, including latency/sample count/contract accuracy and evidence path, without rerunning them. Its A800 section says `NOT_RUN` until an A800 manifest exists. No numeric result is copied from a prose-only 3B report.

- [ ] **Step 8: Validate source documents and media-tool CLI without fabricating runtime artifacts**

Run: `python tools/render_closed_loop_video.py --help`

Run: `python -m pytest integration/tests/test_reproduction_docs.py -q`

Expected: renderer help exits 0 and documentation structure tests pass; no GPU test, PDF render, or video render runs yet.

- [ ] **Step 9: Commit human-facing reproduction artifacts**

```powershell
git add README_REPRO.md notebooks/reproduce.ipynb submission/technical_solution.md tools/render_closed_loop_video.py tools/run_qwen_carla_closed_loop.py integration/tests/test_reproduction_docs.py
git commit -m "feat: add reproduction documentation and media tooling"
```

### Task 10: Produce the RTX 5070 Reference Run Without Redundant Evaluation

**Files:**
- Create from runtime output: `metrics/reference_5070/run_manifest.json`
- Create from runtime output: `metrics/reference_5070/environment.json`
- Create from runtime output: `metrics/reference_5070/model_manifest.json`
- Create from runtime output: `metrics/reference_5070/metrics/*.json`
- Create from runtime output: `metrics/reference_5070/logs/*.log`
- Create from runtime output: `metrics/reference_5070/raw/*.jsonl`
- Create: `metrics/reference_5070/README.md`
- Create: `tools/promote_reference_run.py`
- Create: `integration/tests/test_promote_reference_run.py`
- Create from real evidence: `submission/技术方案.pdf`
- Create from real evidence: `submission/demo/carla_closed_loop.mp4`
- Create: `integration/tests/test_submission_media.py`

**Interfaces:**
- Consumes: built CUDA 13.2 images, frozen release assets, documentation sources, and `run.sh` modes from Tasks 5–9.
- Produces: one honest 5070 reference run or one preserved early-stop run; accuracy/scenarios execute only when the measured dynamic-frame P95 allows them.

- [ ] **Step 1: Write a failing promotion-integrity test**

```python
import json
from pathlib import Path

import pytest

from tools.promote_reference_run import promote_reference_run


def test_promotion_rejects_running_or_incomplete_run(tmp_path: Path) -> None:
    source = tmp_path / "runs/run-1"
    source.mkdir(parents=True)
    (source / "run_manifest.json").write_text(
        json.dumps({"run_id": "run-1", "status": "RUNNING"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="RUNNING"):
        promote_reference_run(source, tmp_path / "reference", "RTX 5070 reference")
```

- [ ] **Step 2: Run the promotion test and confirm the helper is absent**

Run: `python -m pytest integration/tests/test_promote_reference_run.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: tools.promote_reference_run`.

- [ ] **Step 3: Implement immutable evidence promotion**

```python
def promote_reference_run(source: Path, destination: Path, hardware_label: str) -> None:
    manifest_path = source / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") == "RUNNING":
        raise ValueError("cannot promote a RUNNING manifest")
    required = ("environment.json", "model_manifest.json", "metrics", "logs")
    missing = [name for name in required if not (source / name).exists()]
    if missing:
        raise FileNotFoundError("incomplete run evidence: " + ", ".join(missing))
    if destination.exists():
        raise FileExistsError(f"reference destination already exists: {destination}")
    shutil.copytree(source, destination)
    (destination / "README.md").write_text(
        f"# {hardware_label}\n\nrun_id: `{manifest['run_id']}`\n\nstatus: `{manifest['status']}`\n",
        encoding="utf-8",
    )
```

The CLI calls this function. It verifies file hashes recorded by the source manifest before `copytree`, never rewrites raw JSON/JSONL/log files, and appends honest limitations to README according to the final status.

- [ ] **Step 4: Run the promotion tests**

Run: `python -m pytest integration/tests/test_promote_reference_run.py -q`

Expected: PASS for completed fixtures and explicit rejection of RUNNING, incomplete, hash-mismatched, or pre-existing destinations.

- [ ] **Step 5: Build the three pinned images once**

Run:

```powershell
$asrSource = (Resolve-Path weights/SenseVoiceSmall).Path
python tools/build_submission_package.py --prepare-only --profile qwen3vl-2b-int4 --qwen-source models/Qwen3-VL-2B-Instruct-GPTQ-Int4 --asr-source "$asrSource" --staging release_assets
$releaseCommit = (git rev-parse --short=12 HEAD).Trim()
docker build -f docker/Dockerfile.controller -t "carla-controller:$releaseCommit" .
docker build -f docker/Dockerfile.qwen-cu132 -t qwen-vllm-cu132:qwen3vl-2b-int4 .
docker pull carlasim/carla:0.9.16
docker tag carlasim/carla:0.9.16 carla-simulator:0.9.16
```

If `weights/SenseVoiceSmall` is absent, run `wsl bash weights/download_asr_fallback.sh` once before this step; it must fetch and verify revision `7bf452403abd7353a300cd760f7adae7701c92c1`. Expected: staging verifies Qwen/ASR/dataset/source hashes, all image commands exit 0, and no container has started yet.

- [ ] **Step 6: Run preflight and inspect the captured environment before spending GPU time**

Run: `.\run.ps1 preflight --profile rtx5070`

Expected: PASS; environment says RTX 5070, CUDA userspace 13.2, profile `qwen3vl-2b-int4`, verified Marlin configuration, three image digests, immutable model revision, and valid weight/dataset hashes.

- [ ] **Step 7: Run exactly one smoke scenario**

Run: `.\run.ps1 smoke --profile rtx5070`

Expected: one WAV traverses ASR, Qwen, target/safety arbitration, and one physical CARLA basic-control scenario; output contains a final actor state and no development-path access.

- [ ] **Step 8: Run the latency-first evaluation once**

Run: `.\run.ps1 evaluate --profile rtx5070`

Expected: 5 warm-ups are excluded, then 10 dynamic-frame samples are measured. If end-to-end P95 exceeds 300 ms, status is `EARLY_STOP` and no accuracy/scenario collection runs. If it is at most 300 ms, the frozen accuracy set and exactly three representative physical scenarios run.

- [ ] **Step 9: Copy—not recompute—the completed run evidence into the reference directory**

Read the run ID pointer written by the preceding command:

```powershell
$runId = (Get-Content output/latest_run_id.txt -Raw).Trim()
python tools/promote_reference_run.py --run-dir "output/runs/$runId" --destination metrics/reference_5070 --hardware-label "RTX 5070 reference"
```

`promote_reference_run.py` must verify hashes and refuse an incomplete `RUNNING` manifest. It copies raw evidence unchanged and writes `metrics/reference_5070/README.md` with the actual status and limitations.

- [ ] **Step 10: Run demo only if smoke succeeded**

Run: `.\run.ps1 demo --profile rtx5070`

Expected: a physical closed-loop run creates real frame/audio/action records; a failure stays labeled as failure.

- [ ] **Step 11: Render the closed-loop video from that real demo run**

```powershell
$demoRunId = (Get-Content output/latest_run_id.txt -Raw).Trim()
python tools/render_closed_loop_video.py --run-dir "output/runs/$demoRunId" --output submission/demo/carla_closed_loop.mp4 --fps 20
ffprobe -v error -show_entries stream=codec_name -show_entries format=duration -of json submission/demo/carla_closed_loop.mp4
```

Expected: H.264 video plus AAC audio, duration at least 20 seconds, command/ASR/action/speed/status overlays, and the actual scenario outcome.

- [ ] **Step 12: Render and visually verify the technical PDF using the PDF skill**

Render `submission/technical_solution.md` to `submission/技术方案.pdf` after substituting values only through the verified `metrics/reference_5070` reader. Inspect every rendered page; the score table, architecture diagram, Chinese text, hashes, and limitations must be legible and unclipped. The A800 section remains `NOT_RUN` because this task is executed on RTX 5070.

- [ ] **Step 13: Execute the notebook against the promoted reference run**

```powershell
New-Item -ItemType Directory -Force output/reference_5070 | Out-Null
Copy-Item metrics/reference_5070/* output/reference_5070/ -Recurse -Force
docker compose --env-file config/repro/rtx5070.env -f docker/compose.yaml run --rm -e CARLA_REPRO_RUN_DIR=/output/reference_5070 controller jupyter nbconvert --to notebook --execute /app/notebooks/reproduce.ipynb --output-dir /output/reference_5070 --output reproduce.executed.ipynb --ExecutePreprocessor.timeout=120
```

Expected: exit code 0; every displayed result has the promoted run ID, and unavailable accuracy/stability sections display their recorded `not_run_reason` instead of zero or a fabricated pass.

- [ ] **Step 14: Validate the final media files**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_submission_media_are_real_files() -> None:
    assert (ROOT / "submission/技术方案.pdf").stat().st_size > 50_000
    assert (ROOT / "submission/demo/carla_closed_loop.mp4").stat().st_size > 1_000_000
```

Run: `python -m pytest integration/tests/test_submission_media.py -q`

Expected: PASS. The test fixture additionally runs `ffprobe` and checks H.264, AAC, and duration `>= 20.0` seconds.

- [ ] **Step 15: Do not run stability on 5070 unless the official latency line is reached**

Run only when the reference manifest has `end_to_end_ms.p95 <= 150.0`: `.\run.ps1 stability --profile rtx5070`

Expected: 30-minute stability metrics. Otherwise skip this command and record `not_run_reason="end_to_end_p95_above_150ms"` in the reference README.

- [ ] **Step 16: Commit only raw-backed reference evidence and generated media**

```powershell
git add metrics/reference_5070 tools/promote_reference_run.py integration/tests/test_promote_reference_run.py submission/技术方案.pdf submission/demo/carla_closed_loop.mp4 integration/tests/test_submission_media.py
git commit -m "test: record RTX 5070 reference evidence"
```

### Task 11: Assemble and Verify the Final Independent Package

**Files:**
- Create: `integration/tests/test_submission_release.py`
- Create from metrics: `HANDOFF_B_REPRO_0804.md`
- Create from builder: `dist/carla-language-control-submission/`
- Modify: `README_REPRO.md` only if verification exposes an incorrect command.

**Interfaces:**
- Consumes: all committed deliverables from Tasks 1–10 and three built Docker images.
- Produces: a validated release directory containing `image.tar`, Compose, scripts, README, configs, manifests, datasets, scenarios, audio, notebook, metrics/logs, technical PDF, demo video, and release manifest.

- [ ] **Step 1: Write a release-content test against the final directory**

```python
from pathlib import Path


def test_release_contains_independent_reproduction_contract() -> None:
    release = Path("dist/carla-language-control-submission")
    required = {
        "image.tar",
        "image.tar.sha256",
        "docker-compose.yml",
        "run.sh",
        "stop.sh",
        "README.md",
        "config/common.env",
        "config/rtx5070.env",
        "config/a800-safe.env",
        "config/a800-optimized.env",
        "weights/model_manifest.json",
        "weights/SHA256SUMS",
        "weights/download_fallback.sh",
        "weights/download_asr_fallback.sh",
        "weights/download_optional_models.sh",
        "datasets/CARLA-Language-Benchmark/dataset_card.json",
        "datasets/frozen_validation/asr/manifest.json",
        "datasets/frozen_validation/multimodal/cases.jsonl",
        "datasets/frozen_validation/full_chain_latency_v1.json",
        "scenarios/smoke/S01_set_speed_20.json",
        "scenarios/regression/REG_008_challenge_pedestrian.json",
        "scenarios/safety_D/D07_low_ttc_emergency_brake.json",
        "samples/audio/smoke_set_speed_20.wav",
        "samples/commands.jsonl",
        "notebooks/reproduce.ipynb",
        "docs/技术方案.pdf",
        "docs/HANDOFF_B_REPRO_0804.md",
        "demo/carla_closed_loop.mp4",
        "metrics/reference_5070/run_manifest.json",
        "metrics/historical_5070/raw/qwen25_3b_awq_0803_frozen320_baseline.json",
        "metrics/historical_5070/raw/qwen3vl_2b_fp8_vllm_cu132_latency_gate.json",
        "metrics/historical_5070/raw/qwen3vl_2b_gptq_int4_marlin_vllm_cu132_latency_gate_prompt_v3.json",
        "release_manifest.json",
    }
    assert not [path for path in sorted(required) if not (release / path).is_file()]
    assert any((release / "metrics/reference_5070/logs").iterdir())
    assert any((release / "metrics/reference_5070/raw").iterdir())
```

- [ ] **Step 2: Run the release test and confirm no assembled package exists yet**

Run: `python -m pytest integration/tests/test_submission_release.py -q`

Expected: FAIL listing missing files under `dist/carla-language-control-submission`.

- [ ] **Step 3: Run the consolidated code regression once**

Run: `python -m pytest integration/tests qwen_service/tests -q`

Expected: PASS. If a failure is unrelated to the release changes and predates the plan, record the exact test and existing cause; do not hide it or rerun unrelated GPU benchmarks.

- [ ] **Step 4: Render the handoff from raw-backed metrics and validate A800 commands**

Run:

```powershell
python tools/build_submission_package.py --render-handoff HANDOFF_B_REPRO_0804.md --reference-run metrics/reference_5070 --profile qwen3vl-2b-int4
```

The generated handoff contains exactly these sections: `Scope`, `Default Route`, `RTX 5070 Results`, `A800 Status`, `Evidence Index`, `Reproduction`, `Known Limits`, and `Next Operator`. It reads latency/accuracy/scenario values and `not_run_reason` directly from reference JSON, records the fixed INT4/FP8/3B revisions, identifies the actual kernel evidence, and writes `A800 Status: NOT_RUN` until an A800 manifest exists. It never quotes the prose-only 3B reports as validated raw evidence.

Both `HANDOFF_B_REPRO_0804.md` and `README_REPRO.md` contain this exact A800 sequence:

```bash
docker load -i image.tar
./run.sh preflight --profile a800-safe
./run.sh evaluate --profile a800-safe
./stop.sh
./run.sh preflight --profile a800-optimized
./run.sh evaluate --profile a800-optimized
./run.sh stability --profile a800-optimized
./stop.sh
```

They state that `stability` runs only after optimized evaluation reaches or approaches the official latency line and that A800 results must be generated on the A800, never copied from 5070 evidence.

- [ ] **Step 5: Build the release directory and archive**

Run:

```powershell
python tools/build_submission_package.py --name carla-language-control-submission --profile qwen3vl-2b-int4 --reference-run metrics/reference_5070 --output dist
```

Expected: builder validates every hash, copies the handoff into `docs/`, runs `docker save` once, writes `release_manifest.json`, and exits 0. The manifest includes Git commit, three image RepoDigests, Qwen revision, vLLM wheel SHA256, CUDA userspace 13.2, dataset hash, reference run ID, PDF hash, video hash, and handoff hash.

- [ ] **Step 6: Validate archive identity and release contents**

Run: `python -m pytest integration/tests/test_submission_release.py -q`

Run: `Get-FileHash -Algorithm SHA256 dist/carla-language-control-submission/image.tar`

Expected: test PASS and the printed digest exactly matches `image.tar.sha256`.

- [ ] **Step 7: Verify a no-host-dependency smoke launch from the assembled directory**

Open a new Bash terminal in `dist/carla-language-control-submission`, set `HF_HOME` to an empty temporary directory, then run:

```bash
export HF_HOME="$(mktemp -d)"
docker load -i image.tar
./run.sh preflight --profile rtx5070
./run.sh smoke --profile rtx5070
./stop.sh
```

Expected: PASS without reading the repository source tree, host venv, host model cache, or network. Logs and manifests appear only under the release's `output/runs`.

- [ ] **Step 8: Execute the packaged notebook against the packaged reference metrics**

Run:

```bash
mkdir -p output/reference_5070
cp -a metrics/reference_5070/. output/reference_5070/
docker compose --env-file config/rtx5070.env -f docker-compose.yml run --rm \
  -e CARLA_REPRO_RUN_DIR=/output/reference_5070 controller \
  jupyter nbconvert --to notebook --execute /app/notebooks/reproduce.ipynb \
  --output-dir /output/reference_5070 --output reproduce.executed.ipynb \
  --ExecutePreprocessor.timeout=120
```

Expected: exit 0 and all displayed hashes/run IDs match `release_manifest.json`.

- [ ] **Step 9: Commit release validation and handoff, never the multi-gigabyte tar**

```powershell
git add integration/tests/test_submission_release.py README_REPRO.md HANDOFF_B_REPRO_0804.md tools/build_submission_package.py
git commit -m "docs: finalize independent reproduction handoff"
```

- [ ] **Step 10: Verify repository state and push the validated progress to the rstar branch**

Run:

```powershell
git status --short
git log -1 --oneline
git push origin HEAD:carla_driving_rstar
```

Expected: only pre-existing user files such as the separately modified `detail_answer.md` remain unstaged; the push updates `origin/carla_driving_rstar` to the verified handoff commit. Do not add or clean unrelated user artifacts to make the status appear empty.

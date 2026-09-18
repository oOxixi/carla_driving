"""Adapters for the three measurement chains.

The harness never re-implements planner logic.  It drives the *same* objects
that A1/A3/A4 ship (``StudentPreprocessor``, ``StudentPlannerV0``,
``StudentPlanAdapter``, ``PlanValidator``) and only inserts timestamps between
their calls.  ``verify_consistency()`` proves that this instrumentation path and
``StudentBackend.infer`` produce the same plan for the same request.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any, Mapping, Protocol, Sequence

from .identity import (
    UNRESOLVED,
    CandidateIdentity,
    git_head,
    identity_from_artifact,
    identity_from_weight_manifest,
    sha256_file,
)
from .stages import STAGE_INDEX, StageTrace

_STAGE_ORDER = tuple(sorted(STAGE_INDEX, key=lambda name: STAGE_INDEX[name]))


class AdapterError(RuntimeError):
    """The adapter could not be constructed or driven."""


@dataclass(frozen=True, slots=True)
class RuntimeCapabilities:
    full_chain: bool
    model_only: bool
    plan_validator: bool
    stage_source: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_chain": self.full_chain,
            "model_only": self.model_only,
            "plan_validator": self.plan_validator,
            "stage_source": self.stage_source,
            "notes": list(self.notes),
        }


class PlannerRuntime(Protocol):
    name: str
    identity: CandidateIdentity
    capabilities: RuntimeCapabilities

    def infer(
        self,
        request: Mapping[str, Any],
        *,
        case_id: str,
        round_index: int,
        phase: str = "measured",
    ) -> tuple[Mapping[str, Any] | None, StageTrace]:
        ...

    def close(self) -> None:
        ...


class _RepoModules:
    """Lazy import of the challenge-side modules under test."""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / "challenge").is_dir():
            raise AdapterError(f"not a carla_driving checkout: {self.repo_root}")
        if str(self.repo_root) not in sys.path:
            sys.path.insert(0, str(self.repo_root))
        self._cache: dict[str, Any] = {}

    def get(self, dotted: str) -> Any:
        if dotted in self._cache:
            return self._cache[dotted]
        if "." in dotted:
            module_name, _, attribute = dotted.rpartition(".")
        else:
            module_name, attribute = dotted, ""
        try:
            module = __import__(module_name, fromlist=[attribute] if attribute else [])
            value = getattr(module, attribute) if attribute else module
        except Exception as error:  # pragma: no cover - import guard
            raise AdapterError(f"cannot import {dotted}: {type(error).__name__}: {error}") from error
        self._cache[dotted] = value
        return value

    def has(self, dotted: str) -> bool:
        try:
            self.get(dotted)
        except AdapterError:
            return False
        return True


def state_dict_fingerprint(model: Any) -> str:
    """Deterministic SHA256 over a model's parameters.

    The in-process chain has no weight file on disk, so without this the run's
    identity would be ``UNRESOLVED`` and the evidence could not say *which*
    weights produced the numbers.  Hashing the tensors gives the torch path an
    artifact identity that is reproducible (same seed, same weights, same hash).
    """
    import hashlib

    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(tensor.detach().to("cpu").contiguous().numpy().tobytes())
        digest.update(b"\n")
    return digest.hexdigest()


class InProcessStudentRuntime:
    """Full-chain measurement reusing A1/A3 objects with B3 timestamps."""

    name = "inprocess-torch"

    def __init__(
        self,
        repo_root: str | Path,
        *,
        weights: str | Path | None = None,
        weights_manifest: str | Path | None = None,
        dataset_version: str = UNRESOLVED,
        seed: int | None = 20260911,
    ) -> None:
        self.modules = _RepoModules(repo_root)
        self.repo_root = self.modules.repo_root
        StudentPlannerV0 = self.modules.get("challenge.student.model.StudentPlannerV0")
        StudentPreprocessor = self.modules.get("challenge.student.preprocess.StudentPreprocessor")
        StudentPlanAdapter = self.modules.get("challenge.planner.student_adapter.StudentPlanAdapter")
        validation_scene = self.modules.get("challenge.planner.common.validation_scene")

        torch = self.modules.get("torch")
        self._torch = torch
        # A1 freezes `torch.manual_seed(20260911)` before instantiation so the
        # structure is reproducible; the harness must do the same, otherwise
        # two runs over one frozen request set produce different plans.
        self.seed = seed
        if seed is not None:
            torch.manual_seed(seed)
        self.model = StudentPlannerV0()
        self.model_id = str(getattr(self.model, "model_id", "student-v0-r3-fp32"))
        self.config_id = str(getattr(self.model.config, "config_id", UNRESOLVED))
        if weights is not None:
            payload = torch.load(Path(weights), map_location="cpu", weights_only=True)
            self.model.load_state_dict(payload)
        self.model.eval()
        self._preprocessor = StudentPreprocessor(self.model.contract)
        self._adapter = StudentPlanAdapter(model_id=self.model_id)
        self._validation_scene = validation_scene

        notes: list[str] = []
        self._validator = None
        try:
            import jsonschema  # noqa: F401

            jsonschema_available = True
        except ImportError:
            jsonschema_available = False
        if jsonschema_available:
            InterfaceRegistry = self.modules.get("runtime.interface_registry.InterfaceRegistry")
            PlanValidator = self.modules.get("runtime.plan_validator.PlanValidator")
            self._validator = PlanValidator(registry=InterfaceRegistry(self.repo_root / "interfaces"))
        else:
            notes.append(
                "PlanValidator skipped: jsonschema is not installed in this interpreter"
            )
        if weights is None:
            notes.append(
                f"random-initialized weights (torch.manual_seed={self.seed}): "
                "structure/toolchain validation only"
            )

        if weights is not None and weights_manifest is not None:
            self.identity = identity_from_weight_manifest(weights, weights_manifest)
        elif weights is not None:
            self.identity = identity_from_artifact(
                weights,
                model_id=self.model_id,
                config_id=self.config_id,
                dataset_version=dataset_version,
            )
        else:
            self.identity = CandidateIdentity(
                git_sha=git_head(self.repo_root),
                model_id=self.model_id,
                model_sha256=state_dict_fingerprint(self.model),
                dataset_version=(
                    dataset_version
                    if dataset_version != UNRESOLVED
                    else "NOT_APPLICABLE_RANDOM_INIT"
                ),
                config_id=self.config_id,
            )
        self.capabilities = RuntimeCapabilities(
            full_chain=True,
            model_only=True,
            plan_validator=self._validator is not None,
            stage_source="PARTIAL" if self._validator is None else "INSTRUMENTED",
            notes=tuple(notes),
        )

    def infer(
        self,
        request: Mapping[str, Any],
        *,
        case_id: str,
        round_index: int,
        phase: str = "measured",
    ) -> tuple[Mapping[str, Any] | None, StageTrace]:
        trace = StageTrace(
            trace_id=str(request.get("request_id", case_id)),
            case_id=case_id,
            round_index=round_index,
            phase=phase,
            stage_source=self.capabilities.stage_source,
        )
        torch = self._torch
        trace.mark("input_arrival")
        try:
            rgb = self._preprocessor._rgb(request.get("rgb_ref"))
            trace.mark("preprocess_end")
            text_tokens = self._preprocessor._text(str(request["source_text"]))
            targets = self._preprocessor._targets(request["targets"])
            state = self._preprocessor._state(request)
            trace.mark("packing_end")
            trace.mark("inference_start")
            with torch.inference_mode():
                raw_outputs = self.model(rgb, text_tokens, targets, state)
            trace.mark("inference_end")
            outputs = {
                key: value.detach().to("cpu").contiguous()
                for key, value in dict(raw_outputs).items()
            }
            trace.mark("postprocess_end")
            plan = self._adapter.decode(request, outputs)
            trace.mark("adapter_end")
            if self._validator is None:
                trace.mark("plan_ready")
                trace.finish(
                    "READY",
                    reason_code="PLAN_UNVALIDATED",
                    detail=(
                        "plan_validator_skipped:jsonschema_missing; "
                        "plan_validation_ms is not a real validation cost"
                    ),
                )
                return plan, trace
            validated = self._validator.validate(
                plan,
                scene=self._validation_scene(request),
                expected_request_id=request["request_id"],
                expected_command_id=request["command_id"],
                now_ns=request["created_at_ns"],
                allow_confirmation=True,
            )
            trace.mark("plan_ready")
            trace.finish("READY", reason_code=str(validated.get("reason_code", "")))
            return validated, trace
        except Exception as error:
            trace.finish(
                "ERROR",
                reason_code="ADAPTER_EXCEPTION",
                detail=f"{type(error).__name__}: {error}",
            )
            return None, trace

    def verify_consistency(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Prove the instrumented path equals ``StudentBackend.infer`` output."""
        if self._validator is None:
            return {
                "status": "SKIPPED",
                "reason": "jsonschema_missing: StudentBackend.infer cannot be driven",
            }
        StudentBackend = self.modules.get("challenge.planner.student_backend.StudentBackend")
        try:
            backend = StudentBackend(model=self.model, weights=None)
            reference = backend.infer(request)
        except Exception as error:
            return {
                "status": "ERROR",
                "reason": f"{type(error).__name__}: {error}",
                "backend": "StudentBackend.infer",
            }
        with self._torch.inference_mode():
            raw = self.model(*self._preprocessor(request).as_tuple())
        plan = self._adapter.decode(
            request,
            {
                key: value.detach().to("cpu").contiguous()
                for key, value in dict(raw).items()
            },
        )
        validated = self._validator.validate(
            plan,
            scene=self._validation_scene(request),
            expected_request_id=request["request_id"],
            expected_command_id=request["command_id"],
            now_ns=request["created_at_ns"],
            allow_confirmation=True,
        )
        same = json.dumps(validated, sort_keys=True) == json.dumps(
            dict(reference), sort_keys=True
        )
        return {
            "status": "PASS" if same else "MISMATCH",
            "backend": "StudentBackend.infer",
            "instrumented": "harness stage path",
            "plan_step_count": len(validated.get("steps", ()))
            if isinstance(validated, Mapping)
            else None,
        }

    def close(self) -> None:
        return None


class OnnxModelRuntime:
    """Model-only chain: the X86 stand-in for `hrt_model_exec perf`."""

    name = "onnx-model-only"

    def __init__(self, repo_root: str | Path, onnx_path: str | Path) -> None:
        self.modules = _RepoModules(repo_root)
        self.repo_root = self.modules.repo_root
        self.onnx_path = Path(onnx_path).resolve()
        if not self.onnx_path.is_file():
            raise AdapterError(f"ONNX artifact not found: {self.onnx_path}")
        try:
            import onnxruntime
        except ImportError as error:  # pragma: no cover
            raise AdapterError("onnxruntime is required for the ONNX chain") from error
        self._ort = onnxruntime
        options = onnxruntime.SessionOptions()
        options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = onnxruntime.InferenceSession(
            str(self.onnx_path),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.input_names = [value.name for value in self.session.get_inputs()]
        self.output_names = [value.name for value in self.session.get_outputs()]
        metadata = dict(self.session.get_modelmeta().custom_metadata_map)
        StudentPreprocessor = self.modules.get("challenge.student.preprocess.StudentPreprocessor")
        StudentPlanAdapter = self.modules.get("challenge.planner.student_adapter.StudentPlanAdapter")
        self._preprocessor = StudentPreprocessor()
        self._adapter = StudentPlanAdapter(
            model_id=str(metadata.get("model_id", UNRESOLVED))
        )
        self._metadata = metadata
        self.model_id = str(metadata.get("model_id", UNRESOLVED))
        self.config_id = str(metadata.get("config_id", UNRESOLVED))
        self.identity = CandidateIdentity(
            git_sha=str(metadata.get("source_git_sha", UNRESOLVED)),
            model_id=self.model_id,
            model_sha256=sha256_file(self.onnx_path),
            dataset_version=str(metadata.get("dataset_version", UNRESOLVED)),
            config_id=self.config_id,
        )
        self.capabilities = RuntimeCapabilities(
            full_chain=True,
            model_only=True,
            plan_validator=False,
            stage_source="INSTRUMENTED",
            notes=(
                "model-only chain; adapter runs on host tensors converted from numpy",
                "no PlanValidator: A4/J6P runtime owns the deployed validation step",
            ),
        )

    def infer(
        self,
        request: Mapping[str, Any],
        *,
        case_id: str,
        round_index: int,
        phase: str = "measured",
    ) -> tuple[Mapping[str, Any] | None, StageTrace]:
        trace = StageTrace(
            trace_id=str(request.get("request_id", case_id)),
            case_id=case_id,
            round_index=round_index,
            phase=phase,
        )
        trace.mark("input_arrival")
        try:
            rgb = self._preprocessor._rgb(request.get("rgb_ref"))
            trace.mark("preprocess_end")
            text_tokens = self._preprocessor._text(str(request["source_text"]))
            targets = self._preprocessor._targets(request["targets"])
            state = self._preprocessor._state(request)
            feed = {
                "rgb": rgb.numpy(),
                "text_tokens": text_tokens.numpy(),
                "targets": targets.numpy(),
                "state": state.numpy(),
            }
            missing = [name for name in self.input_names if name not in feed]
            if missing:
                raise AdapterError(f"ONNX inputs not produced by the preprocessor: {missing}")
            trace.mark("packing_end")
            trace.mark("inference_start")
            raw = self.session.run(None, feed)
            trace.mark("inference_end")
            outputs = {
                name: value for name, value in zip(self.output_names, raw, strict=True)
            }
            trace.mark("postprocess_end")
            torch = self.modules.get("torch")
            tensors = {
                name: torch.from_numpy(value) for name, value in outputs.items()
            }
            plan = self._adapter.decode(request, tensors)
            trace.mark("adapter_end")
            trace.mark("plan_ready")
            trace.finish(
                "READY",
                reason_code=str(plan.get("reason_code", "")),
                detail="plan_validator_not_part_of_model_only_chain",
            )
            return plan, trace
        except Exception as error:
            trace.finish(
                "ERROR",
                reason_code="ADAPTER_EXCEPTION",
                detail=f"{type(error).__name__}: {error}",
            )
            return None, trace

    def bench_model_only(
        self,
        request: Mapping[str, Any],
        *,
        iterations: int = 10,
        warmup: int = 5,
        case_id: str = "",
    ) -> list[StageTrace]:
        """Pure forward-pass timing, matching the `perf` tool convention."""
        tensors = self._preprocessor(request)
        feed = {
            "rgb": tensors.rgb.numpy(),
            "text_tokens": tensors.text_tokens.numpy(),
            "targets": tensors.targets.numpy(),
            "state": tensors.state.numpy(),
        }
        traces: list[StageTrace] = []
        for index in range(warmup + iterations):
            trace = StageTrace(
                trace_id=f"modelonly-{case_id}-{index:04d}",
                case_id=case_id,
                round_index=index,
                phase="warmup" if index < warmup else "measured",
            )
            trace.mark("input_arrival")
            trace.mark("inference_start")
            self.session.run(None, feed)
            trace.mark("inference_end")
            trace.finish("READY", reason_code="MODEL_ONLY")
            traces.append(trace)
        return traces

    def close(self) -> None:
        return None


class BoardCliRuntime:
    """Drive A4's board runtime as a subprocess.

    Contract: the runtime reads one ``ModelRequest`` JSON object on stdin and
    writes one plan JSON object on stdout.  If the runtime also emits
    ``{"trace": {"<stage>": <monotonic_ns>}}`` the harness uses those marks;
    otherwise the chain is reported as ``NOT_INSTRUMENTED`` and only the
    host-measured envelope is available.
    """

    name = "board-cli"

    def __init__(
        self,
        command: str | Sequence[str],
        *,
        artifact: str | Path | None = None,
        model_id: str = UNRESOLVED,
        config_id: str = UNRESOLVED,
        dataset_version: str = UNRESOLVED,
        timeout_s: float = 30.0,
    ) -> None:
        self.argv = shlex.split(command) if isinstance(command, str) else list(command)
        if not self.argv:
            raise AdapterError("board runtime command must not be empty")
        self.timeout_s = timeout_s
        self.identity = (
            identity_from_artifact(
                artifact,
                model_id=model_id,
                config_id=config_id,
                dataset_version=dataset_version,
            )
            if artifact is not None
            else CandidateIdentity(
                model_id=model_id,
                config_id=config_id,
                dataset_version=dataset_version,
            )
        )
        self.capabilities = RuntimeCapabilities(
            full_chain=True,
            model_only=False,
            plan_validator=True,
            stage_source="NOT_INSTRUMENTED",
            notes=("stage_source is downgraded to INSTRUMENTED only when the runtime emits a trace",),
        )
        self.emitted_trace = False

    def infer(
        self,
        request: Mapping[str, Any],
        *,
        case_id: str,
        round_index: int,
        phase: str = "measured",
    ) -> tuple[Mapping[str, Any] | None, StageTrace]:
        trace = StageTrace(
            trace_id=str(request.get("request_id", case_id)),
            case_id=case_id,
            round_index=round_index,
            phase=phase,
            stage_source="NOT_INSTRUMENTED",
        )
        trace.mark("input_arrival")
        try:
            completed = subprocess.run(
                self.argv,
                input=json.dumps(dict(request), ensure_ascii=False),
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            trace.finish("TIMEOUT", reason_code="RUNTIME_TIMEOUT")
            return None, trace
        if completed.returncode != 0:
            trace.finish(
                "ERROR",
                reason_code="RUNTIME_EXIT",
                detail=f"exit={completed.returncode} stderr={completed.stderr.strip()[:400]}",
            )
            return None, trace
        try:
            payload = json.loads(completed.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as error:
            trace.finish(
                "ERROR", reason_code="RUNTIME_OUTPUT", detail=f"{type(error).__name__}"
            )
            return None, trace
        if not isinstance(payload, Mapping):
            trace.finish("ERROR", reason_code="RUNTIME_OUTPUT", detail="not a JSON object")
            return None, trace
        runtime_trace = payload.pop("trace", None)
        if isinstance(runtime_trace, Mapping) and runtime_trace:
            self.emitted_trace = True
            trace.stage_source = "INSTRUMENTED"
            for stage, value in sorted(
                runtime_trace.items(), key=lambda item: list(_STAGE_ORDER).index(item[0])
            ):
                trace.mark(str(stage), timestamp_ns=int(value))
        else:
            self.capabilities = RuntimeCapabilities(
                full_chain=True,
                model_only=False,
                plan_validator=True,
                stage_source="NOT_INSTRUMENTED",
                notes=(
                    "runtime does not emit trace marks: only the host envelope is measured; "
                    "model-only latency is NOT_AVAILABLE for this chain",
                ),
            )
        trace.mark("plan_ready")
        trace.finish(
            "READY",
            reason_code=str(payload.get("reason_code", "")),
            detail="board_cli_envelope" if trace.stage_source == "NOT_INSTRUMENTED" else "",
        )
        return payload, trace

    def close(self) -> None:
        return None


__all__ = [
    "AdapterError",
    "PlannerRuntime",
    "RuntimeCapabilities",
    "InProcessStudentRuntime",
    "OnnxModelRuntime",
    "BoardCliRuntime",
]

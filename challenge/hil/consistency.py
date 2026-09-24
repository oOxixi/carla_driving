"""Numerical equivalence between the torch path, the ONNX graph, and (later)
the quantized board artifact.

The hardened form of "verify input/output consistency": the same frozen
``ModelRequest`` is pushed through both graphs and **every** output tensor is
compared, not just the decoded plan.  A drift here invalidates any downstream
latency or accuracy comparison, so it runs before board work starts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

import numpy as np

from .identity import UNRESOLVED, sha256_file
from .runtime_adapter import AdapterError, _RepoModules


DEFAULT_RTOL = 1e-4
DEFAULT_ATOL = 1e-5


class OutputSource(Protocol):
    name: str
    identity: Mapping[str, Any]

    def outputs(self, request: Mapping[str, Any]) -> dict[str, np.ndarray]:
        ...

    def close(self) -> None:
        ...


class TorchOutputSource:
    """Raw ``StudentPlannerV0.forward`` outputs as numpy arrays."""

    name = "torch"

    def __init__(
        self,
        repo_root: str | Path,
        *,
        weights: str | Path | None = None,
        seed: int | None = 20260911,
        model_id: str = UNRESOLVED,
        config_id: str = UNRESOLVED,
    ) -> None:
        modules = _RepoModules(repo_root)
        torch = modules.get("torch")
        StudentPlannerV0 = modules.get("challenge.student.model.StudentPlannerV0")
        StudentPreprocessor = modules.get("challenge.student.preprocess.StudentPreprocessor")
        self._torch = torch
        self.seed = seed
        if seed is not None:
            torch.manual_seed(seed)
        self.model = StudentPlannerV0().eval()
        if weights is not None:
            payload = torch.load(Path(weights), map_location="cpu", weights_only=True)
            self.model.load_state_dict(payload)
        self._preprocessor = StudentPreprocessor(self.model.contract)
        self.model_id = str(getattr(self.model, "model_id", model_id))
        self.config_id = str(getattr(self.model.config, "config_id", config_id))
        self.identity = {
            "model_id": self.model_id,
            "config_id": self.config_id,
            "model_sha256": sha256_file(weights) if weights else UNRESOLVED,
            "seed": seed,
        }

    def outputs(self, request: Mapping[str, Any]) -> dict[str, np.ndarray]:
        tensors = self._preprocessor(request)
        with self._torch.inference_mode():
            raw = self.model(*tensors.as_tuple())
        return {
            key: value.detach().to("cpu").numpy().astype(np.float32)
            for key, value in dict(raw).items()
        }

    def close(self) -> None:
        return None


class OnnxOutputSource:
    """Raw ONNX Runtime outputs; also the template for INT8-vs-FP32 checks."""

    name = "onnx"

    def __init__(self, onnx_path: str | Path, repo_root: str | Path) -> None:
        self.path = Path(onnx_path).resolve()
        if not self.path.is_file():
            raise AdapterError(f"ONNX artifact not found: {self.path}")
        try:
            import onnxruntime
        except ImportError as error:  # pragma: no cover - dependency guard
            raise AdapterError("onnxruntime is required") from error
        modules = _RepoModules(repo_root)
        StudentPreprocessor = modules.get("challenge.student.preprocess.StudentPreprocessor")
        self.session = onnxruntime.InferenceSession(
            str(self.path), providers=["CPUExecutionProvider"]
        )
        self.input_names = [value.name for value in self.session.get_inputs()]
        self.output_names = [value.name for value in self.session.get_outputs()]
        self._preprocessor = StudentPreprocessor()
        metadata = dict(self.session.get_modelmeta().custom_metadata_map)
        self.identity = {
            "model_id": str(metadata.get("model_id", UNRESOLVED)),
            "config_id": str(metadata.get("config_id", UNRESOLVED)),
            "model_sha256": sha256_file(self.path),
            "graph": self.path.name,
        }

    def outputs(self, request: Mapping[str, Any]) -> dict[str, np.ndarray]:
        tensors = self._preprocessor(request)
        feed = {
            "rgb": tensors.rgb.numpy(),
            "text_tokens": tensors.text_tokens.numpy(),
            "targets": tensors.targets.numpy(),
            "state": tensors.state.numpy(),
        }
        missing = [name for name in self.input_names if name not in feed]
        if missing:
            raise AdapterError(f"ONNX inputs not produced by the preprocessor: {missing}")
        raw = self.session.run(None, feed)
        return {
            name: np.asarray(value, dtype=np.float32)
            for name, value in zip(self.output_names, raw, strict=True)
        }

    def close(self) -> None:
        return None


def compare_outputs(
    reference: Mapping[str, np.ndarray],
    candidate: Mapping[str, np.ndarray],
    *,
    rtol: float = DEFAULT_RTOL,
    atol: float = DEFAULT_ATOL,
) -> dict[str, Any]:
    """Compare every output tensor; missing or extra keys are failures."""
    ref_keys, cand_keys = set(reference), set(candidate)
    missing = sorted(ref_keys - cand_keys)
    extra = sorted(cand_keys - ref_keys)
    per_output: dict[str, Any] = {}
    worst = 0.0
    all_close = not missing and not extra
    for key in sorted(ref_keys & cand_keys):
        left = np.asarray(reference[key], dtype=np.float64)
        right = np.asarray(candidate[key], dtype=np.float64)
        if left.shape != right.shape:
            per_output[key] = {"shape_mismatch": [list(left.shape), list(right.shape)]}
            all_close = False
            continue
        delta = np.abs(left - right)
        max_abs = float(delta.max()) if delta.size else 0.0
        close = bool(np.allclose(left, right, rtol=rtol, atol=atol))
        worst = max(worst, max_abs)
        per_output[key] = {
            "shape": list(left.shape),
            "max_abs_diff": max_abs,
            "mean_abs_diff": float(delta.mean()) if delta.size else 0.0,
            "allclose": close,
        }
        all_close = all_close and close
    return {
        "passed": bool(all_close),
        "rtol": rtol,
        "atol": atol,
        "max_abs_diff_over_all_outputs": worst,
        "missing_outputs": missing,
        "extra_outputs": extra,
        "per_output": per_output,
    }


def compare_sources(
    reference: OutputSource,
    candidate: OutputSource,
    requests: Sequence[Mapping[str, Any]],
    *,
    rtol: float = DEFAULT_RTOL,
    atol: float = DEFAULT_ATOL,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    passed = True
    worst = 0.0
    for index, request in enumerate(requests):
        try:
            left = reference.outputs(request)
            right = candidate.outputs(request)
        except Exception as error:
            passed = False
            cases.append(
                {
                    "index": index,
                    "request_id": request.get("request_id"),
                    "error": f"{type(error).__name__}: {error}",
                    "passed": False,
                }
            )
            continue
        comparison = compare_outputs(left, right, rtol=rtol, atol=atol)
        worst = max(worst, comparison["max_abs_diff_over_all_outputs"])
        passed = passed and comparison["passed"]
        cases.append(
            {
                "index": index,
                "request_id": request.get("request_id"),
                "passed": comparison["passed"],
                "max_abs_diff": comparison["max_abs_diff_over_all_outputs"],
                "worst_outputs": sorted(
                    (
                        (name, item.get("max_abs_diff"))
                        for name, item in comparison["per_output"].items()
                        if isinstance(item.get("max_abs_diff"), float)
                    ),
                    key=lambda item: item[1],
                    reverse=True,
                )[:3],
                "comparison": comparison,
            }
        )
    return {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference": {"name": reference.name, "identity": dict(reference.identity)},
        "candidate": {"name": candidate.name, "identity": dict(candidate.identity)},
        "request_count": len(requests),
        "passed": passed,
        "rtol": rtol,
        "atol": atol,
        "max_abs_diff_over_all_cases": worst,
        "cases": cases,
        "scope_note": (
            "Raw output tensors are compared, so a pass implies identical decoded "
            "plans under the same adapter; this is a graph-equivalence check, not "
            "an accuracy claim."
        ),
    }


def _canonical(value: Any) -> str:
    import json

    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _compare_plan_values(
    sut: Any,
    reference: Any,
    *,
    path: str,
    rtol: float,
    atol: float,
    structural: list[str],
    numeric: list[tuple[str, float, float]],
) -> None:
    """Compare two plan values: structure exactly, numbers within tolerance.

    A plan carries both discrete semantics (behaviour order, target ids,
    completion types) and numbers derived from the model (confidence, speeds).
    The graph check tolerates ~1e-5 of float32 noise, so the plan check must
    tolerate the same noise instead of demanding bit-identical JSON — otherwise
    a 6e-8 difference in `confidence` would be reported as a plan mismatch.
    """
    if isinstance(sut, Mapping) and isinstance(reference, Mapping):
        if set(sut) != set(reference):
            structural.append(f"{path}: keys differ ({sorted(set(sut) ^ set(reference))})")
            return
        for key in sorted(sut):
            _compare_plan_values(
                sut[key],
                reference[key],
                path=f"{path}.{key}",
                rtol=rtol,
                atol=atol,
                structural=structural,
                numeric=numeric,
            )
        return
    if isinstance(sut, Sequence) and isinstance(reference, Sequence) and not isinstance(
        sut, (str, bytes)
    ) and not isinstance(reference, (str, bytes)):
        if len(sut) != len(reference):
            structural.append(f"{path}: length {len(sut)} != {len(reference)}")
            return
        for index, (left, right) in enumerate(zip(sut, reference)):
            _compare_plan_values(
                left,
                right,
                path=f"{path}[{index}]",
                rtol=rtol,
                atol=atol,
                structural=structural,
                numeric=numeric,
            )
        return
    if (
        isinstance(sut, (int, float))
        and isinstance(reference, (int, float))
        and not isinstance(sut, bool)
        and not isinstance(reference, bool)
    ):
        difference = abs(float(sut) - float(reference))
        numeric.append((path, difference, float(reference)))
        return
    if sut != reference:
        structural.append(f"{path}: {sut!r} != {reference!r}")


def compare_plans(
    runtime: Any,
    cases: Sequence[Any],
    *,
    reference: OutputSource,
    decode_reference: Any,
    rtol: float = DEFAULT_RTOL,
    atol: float = DEFAULT_ATOL,
) -> dict[str, Any]:
    """Compare the plan produced by the **runtime under test** with the reference graph.

    The graph-level check in `compare_sources` never drives the object that is
    actually being measured: it compares two reimplemented forward paths.  The
    B3 audit flagged exactly that ("consistency 未直接调用真实被测 infer"), so
    this function calls ``runtime.infer`` for each frozen case and compares the
    returned plan against the plan decoded from the reference graph's raw
    outputs through the same adapter.

    `decode_reference(request, outputs)` is injected so the comparison can be
    unit-tested without torch; the CLI passes the real `StudentPlanAdapter`.
    """
    rows: list[dict[str, Any]] = []
    for case in cases:
        request = case.request
        case_id = getattr(case, "case_id", request.get("request_id", "?"))
        plan, trace = runtime.infer(request, case_id=str(case_id), round_index=0)
        raw = reference.outputs(request)
        reference_plan = decode_reference(request, raw)
        structural: list[str] = []
        numeric: list[tuple[str, float, float]] = []
        _compare_plan_values(
            plan,
            reference_plan,
            path="plan",
            rtol=rtol,
            atol=atol,
            structural=structural,
            numeric=numeric,
        )
        numeric_violations = [
            f"{path}: |Δ|={difference:.3e} (reference={value:.6g})"
            for path, difference, value in numeric
            if difference > atol + rtol * abs(value)
        ]
        same = not structural and not numeric_violations
        rows.append(
            {
                "case_id": case_id,
                "request_id": request.get("request_id", ""),
                "outcome": trace.outcome,
                "reason_code": trace.reason_code,
                "same_plan": same,
                "structural_diffs": structural,
                "numeric_violations": numeric_violations,
                "numeric_max_abs_diff": max(
                    (difference for _, difference, _ in numeric), default=None
                ),
                "plan_step_count": len(plan.get("steps", ()))
                if isinstance(plan, Mapping)
                else None,
                "reference_step_count": len(reference_plan.get("steps", ()))
                if isinstance(reference_plan, Mapping)
                else None,
                "sut_plan": plan,
                "reference_plan": reference_plan,
            }
        )
    passed = all(row["same_plan"] for row in rows) and bool(rows)
    return {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "plan_vs_reference_graph",
        "runtime": {"name": runtime.name, "identity": getattr(runtime, "identity", None).to_dict()
                    if hasattr(getattr(runtime, "identity", None), "to_dict") else None},
        "reference": {"name": reference.name, "identity": dict(reference.identity)},
        "request_count": len(rows),
        "passed": passed,
        "rtol": rtol,
        "atol": atol,
        "cases": rows,
        "scope_note": (
            "The runtime under test is driven through its own infer path; a pass "
            "means its plans match the reference graph's plans under the same "
            "adapter — structure (behaviour order, target ids, completion types) "
            "exactly, numbers within rtol/atol. It is a consistency check, not an "
            "accuracy claim."
        ),
    }


__all__ = [
    "OutputSource",
    "TorchOutputSource",
    "OnnxOutputSource",
    "compare_outputs",
    "compare_sources",
    "compare_plans",
    "DEFAULT_RTOL",
    "DEFAULT_ATOL",
]

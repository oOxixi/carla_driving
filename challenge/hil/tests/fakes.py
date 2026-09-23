"""A dependency-free planner runtime used by the unit tests."""

from __future__ import annotations

from typing import Any, Mapping

from ..identity import CandidateIdentity
from ..runtime_adapter import RuntimeCapabilities
from ..stages import StageTrace


class FakeRuntime:
    name = "fake"
    identity = CandidateIdentity(
        git_sha="0" * 40,
        model_id="fake-model",
        model_sha256="1" * 64,
        dataset_version="fake-dataset-v1",
        config_id="fake-config",
    )
    capabilities = RuntimeCapabilities(
        full_chain=True,
        model_only=True,
        plan_validator=True,
        stage_source="INSTRUMENTED",
    )

    def __init__(self, *, outcome: str = "READY", behavior: str = "FOLLOW") -> None:
        self.outcome = outcome
        self.behavior = behavior
        self.calls = 0

    def infer(
        self,
        request: Mapping[str, Any],
        *,
        case_id: str,
        round_index: int,
        phase: str = "measured",
    ) -> tuple[Mapping[str, Any] | None, StageTrace]:
        self.calls += 1
        trace = StageTrace(
            trace_id=str(request.get("request_id", case_id)),
            case_id=case_id,
            round_index=round_index,
            phase=phase,
        )
        for offset, stage in enumerate(
            (
                "input_arrival",
                "preprocess_end",
                "packing_end",
                "inference_start",
                "inference_end",
                "postprocess_end",
                "adapter_end",
                "plan_ready",
            )
        ):
            trace.mark(stage, timestamp_ns=1_000_000 + offset * 1_000_000)
        if self.outcome != "READY":
            trace.finish(self.outcome, reason_code="FAKE")
            return None, trace
        trace.finish("READY", reason_code="FAKE")
        plan = {
            "schema_version": "2.0",
            "plan_type": "MANEUVER_SEQUENCE",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "confidence": 0.9,
            "reason_code": "FAKE_OK",
            "steps": [
                {
                    "behavior": self.behavior,
                    "target": {"target_id": None},
                    "on_failure": "SAFE_STOP",
                }
            ],
        }
        return plan, trace

    def close(self) -> None:
        return None

    # The three interface entries A4's contract asks for.  The fake implements
    # them so the "conforming runtime" tests describe a runtime that really does
    # expose `--describe`, batch mode and a model-only path.
    def describe(self) -> Mapping[str, Any]:
        return {
            "git_sha": self.identity.git_sha,
            "model_id": self.identity.model_id,
            "model_sha256": self.identity.model_sha256,
            "dataset_version": self.identity.dataset_version,
            "config_id": self.identity.config_id,
            "precision": "fp32",
            "batch": 1,
            "input_shapes": {
                "rgb": [1, 3, 224, 224],
                "text_tokens": [1, 32],
                "targets": [1, 8, 14],
                "state": [1, 64],
            },
        }

    def run_batch(
        self,
        requests,
    ):
        return [
            self.infer(request, case_id=f"batch-{index:02d}", round_index=0)[0]
            for index, request in enumerate(requests)
        ]

    def run_model_only(self, tensor_dir, *, iterations: int = 1) -> dict[str, Any]:
        raise RuntimeError(
            f"fake runtime has no model weights to run from {tensor_dir}"
        )

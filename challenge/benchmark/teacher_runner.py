"""Teacher inference runner for B2 benchmark replay."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Protocol

from qwen_service.client import QwenServiceClient
from runtime.interface_registry import (
    InterfaceRegistry,
    InterfaceValidationError,
)

from .replay_transport import refresh_replay_deadline


class TeacherClient(Protocol):
    """Minimal inference boundary required by the B2 Teacher runner."""

    def infer(self, request: Mapping[str, Any]) -> Any:
        ...


class TeacherRunnerError(ValueError):
    """Raised when benchmark input cannot be evaluated safely."""


def build_teacher_client(
    base_url: str = "http://127.0.0.1:8765",
    *,
    timeout_s: float = 0.35,
) -> QwenServiceClient:
    """Build the real Teacher client with the frozen replay transport policy."""
    return QwenServiceClient(
        base_url=base_url,
        timeout_s=timeout_s,
        request_transform=refresh_replay_deadline,
    )


def run_teacher_cases(
    cases: Iterable[Mapping[str, Any]],
    *,
    client: TeacherClient,
    registry: InterfaceRegistry | None = None,
) -> list[dict[str, Any]]:
    """
    Run one Teacher inference for every frozen benchmark case.

    Model/service failures become raw failure records instead of disappearing.
    Invalid benchmark inputs fail the whole run before inference begins.
    """
    if not callable(getattr(client, "infer", None)):
        raise TypeError("client must provide infer()")

    materialized = list(cases)
    if not materialized:
        raise TeacherRunnerError("benchmark cases must not be empty")

    active_registry = registry or InterfaceRegistry()
    active_registry.warm(("model_request", "maneuver_plan"))

    prepared: list[tuple[str, str, str, dict[str, Any]]] = []
    seen_sample_ids: set[str] = set()

    # Validate the complete benchmark input before making any inference call.
    for index, case in enumerate(materialized, start=1):
        sample_id, request_id, command_id, request = _prepare_case(
            case,
            index=index,
            registry=active_registry,
        )

        if sample_id in seen_sample_ids:
            raise TeacherRunnerError(
                f"duplicate sample_id in benchmark cases: {sample_id}"
            )

        seen_sample_ids.add(sample_id)
        prepared.append(
            (sample_id, request_id, command_id, request)
        )

    records: list[dict[str, Any]] = []

    for sample_id, request_id, command_id, request in prepared:
        try:
            raw_prediction = client.infer(request)
        except Exception as error:
            records.append(
                _failure_record(
                    sample_id=sample_id,
                    request_id=request_id,
                    command_id=command_id,
                    status="INFERENCE_ERROR",
                    code="QWEN_CLIENT_ERROR",
                    error=error,
                    prediction=None,
                )
            )
            continue

        try:
            plan = active_registry.validate(
                "maneuver_plan",
                raw_prediction,
            )
        except InterfaceValidationError as error:
            records.append(
                _failure_record(
                    sample_id=sample_id,
                    request_id=request_id,
                    command_id=command_id,
                    status="INVALID_OUTPUT",
                    code="INVALID_PLAN_SCHEMA",
                    error=error,
                    prediction=raw_prediction,
                )
            )
            continue

        if plan["request_id"] != request_id:
            error = TeacherRunnerError(
                "Teacher prediction request_id does not match benchmark request"
            )
            records.append(
                _failure_record(
                    sample_id=sample_id,
                    request_id=request_id,
                    command_id=command_id,
                    status="INVALID_OUTPUT",
                    code="REQUEST_ID_MISMATCH",
                    error=error,
                    prediction=plan,
                )
            )
            continue

        if plan["command_id"] != command_id:
            error = TeacherRunnerError(
                "Teacher prediction command_id does not match benchmark request"
            )
            records.append(
                _failure_record(
                    sample_id=sample_id,
                    request_id=request_id,
                    command_id=command_id,
                    status="INVALID_OUTPUT",
                    code="COMMAND_ID_MISMATCH",
                    error=error,
                    prediction=plan,
                )
            )
            continue

        records.append(
            {
                "record_type": "b2_teacher_prediction",
                "sample_id": sample_id,
                "request_id": request_id,
                "command_id": command_id,
                "status": "SUCCESS",
                "prediction": plan,
                "error": None,
            }
        )

    return records


def _prepare_case(
    case: Mapping[str, Any],
    *,
    index: int,
    registry: InterfaceRegistry,
) -> tuple[str, str, str, dict[str, Any]]:
    if not isinstance(case, Mapping):
        raise TeacherRunnerError(
            f"benchmark case {index} must be an object"
        )

    sample_id = case.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise TeacherRunnerError(
            f"benchmark case {index} has invalid sample_id"
        )

    request = case.get("model_request")
    if not isinstance(request, Mapping):
        raise TeacherRunnerError(
            f"benchmark case {sample_id} has invalid model_request"
        )

    try:
        validated_request = registry.validate(
            "model_request",
            request,
        )
    except InterfaceValidationError as error:
        raise TeacherRunnerError(
            f"benchmark case {sample_id} has invalid model_request: {error}"
        ) from error

    request_id = validated_request["request_id"]
    command_id = validated_request["command_id"]

    return (
        sample_id,
        request_id,
        command_id,
        validated_request,
    )


def _failure_record(
    *,
    sample_id: str,
    request_id: str,
    command_id: str,
    status: str,
    code: str,
    error: Exception,
    prediction: Any,
) -> dict[str, Any]:
    return {
        "record_type": "b2_teacher_prediction",
        "sample_id": sample_id,
        "request_id": request_id,
        "command_id": command_id,
        "status": status,
        "prediction": prediction,
        "error": {
            "code": code,
            "type": type(error).__name__,
            "message": str(error),
        },
    }


__all__ = [
    "TeacherClient",
    "TeacherRunnerError",
    "build_teacher_client",
    "run_teacher_cases",
]
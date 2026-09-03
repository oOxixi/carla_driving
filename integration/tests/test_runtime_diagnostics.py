import pytest

from integration.runtime_diagnostics import FailureStage, diagnose_runtime_failure


@pytest.mark.parametrize(
    ("message", "stage"),
    [
        ("generated CARLA route does not satisfy distance contract", FailureStage.ROUTE),
        ("cannot spawn configured scenario walker", FailureStage.ACTOR_SPAWN),
        ("required RGB/LiDAR frame unavailable", FailureStage.PERCEPTION),
        ("Qwen inference exceeded deadline", FailureStage.QWEN),
        ("maneuver precondition failed", FailureStage.PLAN),
        ("invalid control output", FailureStage.CONTROL),
        ("acceptance evidence is incomplete", FailureStage.SCORING),
        ("cannot connect to CARLA port", FailureStage.SETUP),
    ],
)
def test_runtime_failure_has_stable_first_stage(message: str, stage: FailureStage) -> None:
    diagnosis = diagnose_runtime_failure(RuntimeError(message))
    assert diagnosis.stage is stage
    assert diagnosis.exception_type == "RuntimeError"
    assert diagnosis.code


from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from challenge.planner.backend import PlannerBackend
from challenge.planner.student_adapter import StudentPlanAdapter
from challenge.planner.student_backend import StudentBackend
from challenge.planner.teacher_backend import QwenTeacherBackend
from challenge.student.contract import OUTPUT_NAMES, StudentShapeContract
from challenge.student.model import StudentPlannerV0
from challenge.student.preprocess import StudentPreprocessor
from runtime.interface_registry import InterfaceValidationError


ROOT = Path(__file__).resolve().parents[2]


def _request() -> dict:
    return json.loads((ROOT / "interfaces/examples/model_request.json").read_text(encoding="utf-8"))


def test_student_has_fixed_shapes_and_all_structured_heads() -> None:
    contract = StudentShapeContract()
    model = StudentPlannerV0(contract).eval()
    inputs = tuple(torch.zeros(shape) for shape in contract.input_shapes.values())
    with torch.inference_mode():
        outputs = model(*inputs)
    assert len(outputs) == len(OUTPUT_NAMES)
    assert outputs[0].shape == (1, 4)
    assert outputs[1].shape[:2] == (1, 4)
    assert outputs[2].shape == (1, 4, 9)
    assert outputs[4].shape == (1, 4)


def test_fixed_onnx_matches_seeded_pytorch() -> None:
    import onnxruntime as ort

    torch.manual_seed(20260911)
    contract = StudentShapeContract()
    model = StudentPlannerV0(contract).eval()
    inputs = tuple(torch.zeros(shape) for shape in contract.input_shapes.values())
    with torch.inference_mode():
        pytorch_outputs = [value.numpy() for value in model(*inputs)]
    session = ort.InferenceSession(
        str(ROOT / "challenge/student_v0_fp32.onnx"),
        providers=["CPUExecutionProvider"],
    )
    assert [item.shape for item in session.get_inputs()] == [
        list(shape) for shape in contract.input_shapes.values()
    ]
    onnx_outputs = session.run(
        None,
        {name: value.numpy() for name, value in zip(contract.input_shapes, inputs)},
    )
    assert max(
        float(np.max(np.abs(expected - actual)))
        for expected, actual in zip(pytorch_outputs, onnx_outputs)
    ) < 1e-4


def test_preprocessor_is_fixed_shape_and_target_order_preserving() -> None:
    request = _request()
    tensors = StudentPreprocessor()(request)
    contract = StudentShapeContract()
    for value, shape in zip(tensors.as_tuple(), contract.input_shapes.values()):
        assert tuple(value.shape) == shape
    assert tensors.targets[0, 0, 0] == 1.0
    assert tensors.targets[0, 0, 7] == pytest.approx(request["targets"][0]["confidence"])


def test_adapter_grounds_pointer_in_current_request() -> None:
    request = _request()
    model = StudentPlannerV0().eval()
    with torch.inference_mode():
        outputs = list(model(*StudentPreprocessor()(request).as_tuple()))
    outputs[0] = torch.tensor([[9.0, 0.0, 0.0, 0.0]])
    behavior = torch.full_like(outputs[1], -20.0)
    behavior[0, 0, 5] = 20.0  # FOLLOW
    outputs[1] = behavior
    pointer = torch.full_like(outputs[2], -20.0)
    pointer[0, 0, 0] = 20.0
    outputs[2] = pointer
    plan = StudentPlanAdapter().decode(request, outputs)
    assert plan["steps"][0]["target"]["target_id"] == request["targets"][0]["target_id"]
    assert plan["steps"][0]["behavior"] == "FOLLOW"


def test_random_student_backend_returns_valid_confirmation_plan() -> None:
    backend = StudentBackend()
    assert isinstance(backend, PlannerBackend)
    plan = backend.infer(_request())
    assert plan["schema_version"] == "2.0"
    assert plan["request_id"] == _request()["request_id"]
    assert backend.health()[0] is False


def test_teacher_wrapper_rejects_invalid_output() -> None:
    class InvalidTeacher:
        model_id = "invalid"
        production_ready = False

        def infer(self, _request):
            return {"schema_version": "2.0", "steer": 1.0}

    with pytest.raises(Exception):
        QwenTeacherBackend(InvalidTeacher()).infer(_request())


def test_teacher_wrapper_rejects_invalid_request_before_delegate() -> None:
    class Delegate:
        model_id = "unused"
        production_ready = False

        def infer(self, _request):
            raise AssertionError("delegate must not be called")

    request = _request()
    request["unexpected"] = True
    with pytest.raises(InterfaceValidationError):
        QwenTeacherBackend(Delegate()).infer(request)

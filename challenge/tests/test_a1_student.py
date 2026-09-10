from __future__ import annotations

import json
import copy
from pathlib import Path

import numpy as np
import pytest
import torch

from challenge.planner.backend import PlannerBackend
from challenge.planner.student_adapter import StudentPlanAdapter
from challenge.planner.student_backend import StudentBackend, validate_weight_manifest
from challenge.planner.teacher_backend import QwenTeacherBackend
from challenge.planner.frozen_contracts import assert_frozen_contracts
from challenge.student.contract import OUTPUT_NAMES, StudentShapeContract
from challenge.student.model import StudentModelConfig, StudentPlannerV0
from challenge.student.preprocess import StudentPreprocessor
from challenge.student.training_contract import (
    PAD_CLASS_INDICES,
    build_step_mask,
    masked_step_mean,
    padded_target_pointer_index,
    plan_length_to_class,
)
from challenge.export.export_onnx import StudentOnnxExportWrapper
from runtime.interface_registry import InterfaceValidationError
from runtime.interface_registry import InterfaceRegistry


ROOT = Path(__file__).resolve().parents[2]


def _request() -> dict:
    return json.loads((ROOT / "interfaces/examples/model_request.json").read_text(encoding="utf-8"))


def test_student_has_fixed_shapes_and_all_structured_heads() -> None:
    contract = StudentShapeContract()
    model = StudentPlannerV0(contract).eval()
    inputs = tuple(torch.zeros(shape) for shape in contract.input_shapes.values())
    with torch.inference_mode():
        outputs = model(*inputs)
    assert tuple(outputs) == OUTPUT_NAMES
    assert {name: tuple(value.shape) for name, value in outputs.items()} == contract.output_shapes
    assert all(value.dtype == torch.float32 for value in outputs.values())


def test_fixed_onnx_matches_seeded_pytorch() -> None:
    import onnxruntime as ort

    torch.manual_seed(20260911)
    contract = StudentShapeContract()
    model = StudentPlannerV0(contract).eval()
    inputs = tuple(torch.zeros(shape) for shape in contract.input_shapes.values())
    with torch.inference_mode():
        outputs = model(*inputs)
        pytorch_outputs = [outputs[name].numpy() for name in OUTPUT_NAMES]
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


def test_preprocessor_preserves_target_relation_and_speed_hint() -> None:
    left = _request()
    right = copy.deepcopy(left)
    left["targets"][0]["relation"] = "left_adjacent_near"
    right["targets"][0]["relation"] = "right_adjacent_near"
    assert not torch.equal(StudentPreprocessor()(left).targets, StudentPreprocessor()(right).targets)

    slow = _request()
    fast = copy.deepcopy(slow)
    slow["command_hint"] = {"intent": "SET_SPEED", "target_speed_mps": 4.0}
    fast["command_hint"] = {"intent": "SET_SPEED", "target_speed_mps": 10.0}
    assert not torch.equal(StudentPreprocessor()(slow).state, StudentPreprocessor()(fast).state)

    confirm = _request()
    execute = copy.deepcopy(confirm)
    confirm["routing"] = {
        "disposition": "CONFIRM_SAFE", "score": 9, "reasons": ["AMBIGUOUS"],
        "safe_wait_behavior": "STOP",
    }
    execute["routing"] = {
        "disposition": "QWEN_PLAN", "score": 2, "reasons": ["COMPLEX"],
        "safe_wait_behavior": "SLOW_DOWN",
    }
    assert not torch.equal(StudentPreprocessor()(confirm).state, StudentPreprocessor()(execute).state)


def test_vision_encoder_retains_coarse_left_right_position() -> None:
    torch.manual_seed(7)
    encoder = StudentPlannerV0().vision_encoder.eval()
    left = torch.zeros((1, 3, 224, 224))
    right = left.clone()
    left[:, :, 80:112, 40:72] = 1.0
    right[:, :, 80:112, 152:184] = 1.0
    with torch.inference_mode():
        left_features = encoder(left)
        right_features = encoder(right)
    relative_difference = (left_features - right_features).norm() / (
        (left_features.norm() + right_features.norm()) / 2
    )
    assert float(relative_difference) > 0.01


def test_model_config_and_initialization_are_explicit_and_seed_reproducible() -> None:
    config = StudentModelConfig()
    assert config.config_id == "student-v0-r3-structure-20260911"
    assert config.max_target_speed_mps == 50.0
    torch.manual_seed(20260911)
    first = StudentPlannerV0(config=config)
    torch.manual_seed(20260911)
    second = StudentPlannerV0(config=config)
    assert all(
        torch.equal(left, right)
        for left, right in zip(first.state_dict().values(), second.state_dict().values())
    )


def test_onnx_wrapper_preserves_public_output_order() -> None:
    model = StudentPlannerV0().eval()
    wrapper = StudentOnnxExportWrapper(model).eval()
    inputs = tuple(
        torch.zeros(shape, dtype=torch.float32)
        for shape in model.contract.input_shapes.values()
    )
    with torch.inference_mode():
        named = model(*inputs)
        positional = wrapper(*inputs)
    assert len(positional) == len(OUTPUT_NAMES)
    assert all(
        torch.equal(named[name], value)
        for name, value in zip(OUTPUT_NAMES, positional)
    )


def test_plan_padding_and_mask_contract() -> None:
    lengths = torch.tensor([1, 3, 4], dtype=torch.int64)
    mask = build_step_mask(lengths)
    assert mask.dtype == torch.bool
    assert mask.tolist() == [
        [True, False, False, False],
        [True, True, True, False],
        [True, True, True, True],
    ]
    assert plan_length_to_class(lengths).tolist() == [0, 2, 3]
    assert PAD_CLASS_INDICES == {
        "behavior": 13,
        "target_lane": 5,
        "completion_type": 7,
        "on_failure": 1,
    }
    assert padded_target_pointer_index() == 8
    loss = torch.ones((3, 4), dtype=torch.float32)
    assert masked_step_mean(loss, mask).item() == 1.0


def test_adapter_grounds_pointer_in_current_request() -> None:
    request = _request()
    model = StudentPlannerV0().eval()
    with torch.inference_mode():
        outputs = model(*StudentPreprocessor()(request).as_tuple())
    outputs["plan_length_logits"] = torch.tensor([[9.0, 0.0, 0.0, 0.0]])
    behavior = torch.full_like(outputs["behavior_logits"], -20.0)
    behavior[0, 0, 5] = 20.0  # FOLLOW
    outputs["behavior_logits"] = behavior
    pointer = torch.full_like(outputs["target_pointer_logits"], -20.0)
    pointer[0, 0, 0] = 20.0
    outputs["target_pointer_logits"] = pointer
    plan = StudentPlanAdapter().decode(request, outputs)
    assert plan["steps"][0]["target"]["target_id"] == request["targets"][0]["target_id"]
    assert plan["steps"][0]["behavior"] == "FOLLOW"


def test_adapter_repairs_missing_pointer_without_leaving_allowed_behavior() -> None:
    request = _request()
    request["constraints"]["allowed_behaviors"] = ["FOLLOW"]
    model = StudentPlannerV0().eval()
    with torch.inference_mode():
        outputs = model(*StudentPreprocessor()(request).as_tuple())
    outputs["plan_length_logits"] = torch.tensor([[9.0, 0.0, 0.0, 0.0]])
    behavior = torch.full_like(outputs["behavior_logits"], -20.0)
    behavior[0, 0, 5] = 20.0
    outputs["behavior_logits"] = behavior
    pointer = torch.full_like(outputs["target_pointer_logits"], -20.0)
    pointer[0, 0, 8] = 20.0
    pointer[0, 0, 0] = 10.0
    outputs["target_pointer_logits"] = pointer
    plan = StudentPlanAdapter().decode(request, outputs)
    assert plan["steps"][0]["behavior"] == "FOLLOW"
    assert plan["steps"][0]["target"]["target_id"] == request["targets"][0]["target_id"]


def test_adapter_truncates_sequence_after_terminal_stop() -> None:
    request = _request()
    request["constraints"]["allowed_behaviors"] = ["STOP", "SET_SPEED"]
    model = StudentPlannerV0().eval()
    with torch.inference_mode():
        outputs = model(*StudentPreprocessor()(request).as_tuple())
    outputs["plan_length_logits"] = torch.tensor([[0.0, 9.0, 0.0, 0.0]])
    behavior = torch.full_like(outputs["behavior_logits"], -20.0)
    behavior[0, 0, 3] = 20.0
    behavior[0, 1, 1] = 20.0
    outputs["behavior_logits"] = behavior
    plan = StudentPlanAdapter().decode(request, outputs)
    assert [step["behavior"] for step in plan["steps"]] == ["STOP"]


def test_adapter_bounds_plan_id_for_maximum_request_id() -> None:
    request = _request()
    request["request_id"] = "r" * 128
    model = StudentPlannerV0().eval()
    with torch.inference_mode():
        outputs = model(*StudentPreprocessor()(request).as_tuple())
    plan = StudentPlanAdapter().decode(request, outputs)
    assert len(plan["plan_id"]) <= 128


def test_random_student_backend_returns_valid_confirmation_plan() -> None:
    backend = StudentBackend()
    assert isinstance(backend, PlannerBackend)
    plan = backend.infer(_request())
    assert plan["schema_version"] == "2.0"
    assert plan["request_id"] == _request()["request_id"]
    assert backend.health()[0] is False


def test_student_readiness_requires_verified_a3_weight_manifest(tmp_path) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"candidate")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "model_id": "student-v0-r3-fp32",
        "gate_status": "A3_FP32_GATE_PASSED",
        "weights_sha256": "wrong",
        "git_sha": "deadbeef",
        "dataset_version": "test",
        "config_id": "test",
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256"):
        validate_weight_manifest(weights, manifest, expected_model_id="student-v0-r3-fp32")
    with pytest.raises(ValueError, match="requires weights"):
        StudentBackend(weights_manifest=manifest)


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


def test_teacher_health_cannot_promote_non_production_delegate() -> None:
    class TestOnlyDelegate:
        model_id = "test-only"
        production_ready = False

        def health(self):
            return True, "process responds"

        def infer(self, _request):
            raise NotImplementedError

    ready, detail = QwenTeacherBackend(TestOnlyDelegate()).health()
    assert ready is False
    assert "not production-ready" in detail


def test_frozen_contract_fingerprint_is_line_ending_independent(tmp_path) -> None:
    for name in ("model_request", "maneuver_plan"):
        source = ROOT / "interfaces" / f"{name}.schema.json"
        text = source.read_text(encoding="utf-8")
        (tmp_path / f"{name}.schema.json").write_bytes(
            text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
        )
    assert_frozen_contracts(InterfaceRegistry(tmp_path))

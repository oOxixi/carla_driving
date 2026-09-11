from copy import deepcopy

import pytest

from challenge.distillation.dataset import build_mock_records
from challenge.distillation.label_encoder import (
    BEHAVIORS,
    DistillationLabelEncoder,
    LabelEncodingError,
)


def test_teacher_plan_encodes_pointer_padding_and_masks() -> None:
    record = build_mock_records(5)[3]
    request = record["input"]
    plan = deepcopy(record["teacher"]["maneuver_plan"])
    plan["steps"].append({
        "step_id": "step-2",
        "behavior": "RETURN_TO_LANE",
        "target": {
            "target_id": None,
            "target_lane": "CURRENT",
            "target_speed_mps": None,
            "time_gap_s": None,
            "route_direction": "RIGHT",
        },
        "preconditions": ["PERCEPTION_FRESH"],
        "completion": {
            "type": "LANE_CENTERED",
            "value": None,
            "lane": "CURRENT",
            "hold_frames": 3,
        },
        "timeout_s": 10.0,
        "on_failure": "SAFE_STOP",
    })

    labels = DistillationLabelEncoder().encode(request, plan)

    assert labels["plan_length"] == 1
    assert labels["behavior"][:2] == [
        BEHAVIORS.index("AVOID_OBSTACLE"), BEHAVIORS.index("RETURN_TO_LANE"),
    ]
    assert labels["target_pointer"] == [0, 8, 8, 8]
    assert labels["step_mask"] == [True, True, False, False]
    assert labels["target_speed_mask"] == [True, False, False, False]


def test_unknown_teacher_target_is_rejected_instead_of_memorized() -> None:
    record = build_mock_records(3)[2]
    plan = deepcopy(record["teacher"]["maneuver_plan"])
    plan["steps"][0]["target"]["target_id"] = "not-in-current-request"

    with pytest.raises(LabelEncodingError, match="absent"):
        DistillationLabelEncoder().encode(record["input"], plan)


def test_encoder_rejects_more_targets_than_fixed_student_shape() -> None:
    record = build_mock_records(2)[0]
    request = deepcopy(record["input"])
    request["targets"] = [
        {
            "target_id": f"target-{index}", "class": "vehicle",
            "distance_m": 10.0 + index, "relative_speed_mps": 0.0,
            "confidence": 0.9, "relation": "ahead",
        }
        for index in range(9)
    ]

    with pytest.raises(LabelEncodingError, match="supports 8"):
        DistillationLabelEncoder(max_targets=8).encode(
            request, record["teacher"]["maneuver_plan"],
        )


def test_every_mock_record_obeys_the_frozen_teacher_contracts() -> None:
    encoder = DistillationLabelEncoder()
    for record in build_mock_records(25):
        labels = encoder.encode(record["input"], record["teacher"]["maneuver_plan"])
        assert sum(labels["step_mask"]) == 1

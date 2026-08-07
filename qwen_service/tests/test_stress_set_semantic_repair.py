from tools.build_qwen_four_modal_stress_set import (
    _repair_legacy_target_semantics,
)


def _case(relation: str, command: str) -> dict:
    return {
        "case_id": "legacy",
        "voice_command": command,
        "perception": {
            "detected_objects": [{
                "track_id": "pedestrian_1",
                "class": "pedestrian",
                "relation": relation,
            }],
        },
        "expected": {
            "actions": ["SLOW_DOWN", "FOLLOW_VEHICLE"],
            "target_track_id": "pedestrian_1",
        },
    }


def test_repairs_far_ahead_pedestrian_mislabeled_as_adjacent() -> None:
    source = _case("far_ahead", "减速并避让右侧相邻车道的行人")

    repaired, audit = _repair_legacy_target_semantics(source)

    assert source["voice_command"] == "减速并避让右侧相邻车道的行人"
    assert repaired["voice_command"] == "减速并避让前方较远的行人"
    assert repaired["expected"]["actions"] == ["SLOW_DOWN"]
    assert audit is not None
    assert audit["target_relation"] == "far_ahead"


def test_keeps_consistent_adjacent_pedestrian_unchanged() -> None:
    source = _case("right_adjacent", "减速并避让右侧相邻车道的行人")

    repaired, audit = _repair_legacy_target_semantics(source)

    assert repaired == source
    assert audit is None

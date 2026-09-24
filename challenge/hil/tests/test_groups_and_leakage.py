from __future__ import annotations

import json
from pathlib import Path

from ..groups import (
    UNLABELED,
    apply_group_map,
    group_report,
    groups_from_rows,
    read_group_map,
)
from ..leakage import lookup_probe
from ..replay import ReplayCase


def _row(case_id: str, student: str, teacher: str) -> dict:
    return {
        "case_id": case_id,
        "outcome": "READY",
        "structural_failures": "",
        "student_behavior_sequence": student,
        "student_target_sequence": "NONE",
        "teacher_behavior_sequence": teacher,
        "teacher_target_sequence": "NONE",
        "behavior_match_ratio": 0.5,
        "target_match_ratio": 1.0,
    }


def _case(case_id: str, scenario: str, text: str, group: str | None = None) -> ReplayCase:
    return ReplayCase(
        case_id=case_id,
        sample_id=f"sample-{case_id}",
        scenario_id=scenario,
        request={"request_id": case_id, "command_id": case_id, "source_text": text},
        teacher_plan=None,
        rgb_path=None,
        rgb_sha256=None,
        rgb_resolved=False,
        rgb_source="test",
        source_file="test",
        group=group,
    )


def test_labels_come_from_the_case_or_the_map_never_from_the_name():
    labelled = _case("a#0", "VAR_A03_x", "keep lane", group="variant")
    plain = _case("b#0", "SUP_B01_y", "keep lane")
    groups = apply_group_map([labelled, plain])
    assert groups["a#0"] == "VARIANT"
    # The prefix is not interpreted: B3 does not own the grouping.
    assert groups["b#0"] == UNLABELED

    override = {"SUP_B01_y": "SEEN"}
    assert apply_group_map([plain], override)["b#0"] == "SEEN"


def test_group_report_flags_collapse_and_instruction_reuse():
    rows = [
        _row("a#0", "FOLLOW", "STOP"),
        _row("a#1", "FOLLOW", "FOLLOW|STOP"),
        _row("b#0", "STOP", "KEEP_LANE"),
    ]
    groups = {"a#0": "VARIANT", "a#1": "VARIANT", "b#0": "VARIANT"}
    report = group_report(
        rows,
        groups=groups,
        source_texts={"a#0": "keep lane", "a#1": "keep lane", "b#0": "slow down"},
    )
    variant = report["groups"]["VARIANT"]
    assert variant["case_count"] == 3
    assert variant["distinct_student_outputs"] == 2
    assert variant["distinct_teacher_outputs"] == 3
    assert variant["distinct_source_texts"] == 2
    assert variant["cases_per_distinct_source_text"] == 1.5
    assert variant["instruction_text_reuse_signal"] is False
    assert variant["instruction_text_collapsed"] is False
    assert variant["recognized"] is True
    assert report["template_collapse_groups"] == []
    assert report["unrecognized_group_labels"] == []


def test_a_group_whose_teacher_varies_but_student_is_constant_is_flagged():
    rows = [_row("a#0", "FOLLOW", "STOP"), _row("a#1", "FOLLOW", "FOLLOW|STOP")]
    report = group_report(rows, groups={"a#0": "SEEN", "a#1": "SEEN"})
    assert report["template_collapse_groups"] == ["SEEN"]
    assert report["groups"]["SEEN"]["teacher_varies_student_constant"] is True
    assert report["groups"]["SEEN"]["dominant_student_output_share"] == 1.0


def test_unknown_labels_are_reported_verbatim_but_unlabeled_is_not():
    rows = [_row("a#0", "FOLLOW", "STOP"), _row("z#0", "FOLLOW", "STOP")]
    report = group_report(rows, groups={"a#0": "ODD_LABEL", "z#0": UNLABELED})
    assert report["unrecognized_group_labels"] == ["ODD_LABEL"]
    assert UNLABELED not in report["unrecognized_group_labels"]


def test_group_map_reader_accepts_both_shapes(tmp_path: Path):
    flat = tmp_path / "flat.json"
    flat.write_text(json.dumps({"case-1": "seen", "scene-2": "UNSEEN"}), encoding="utf-8")
    assert read_group_map(flat) == {"case-1": "SEEN", "scene-2": "UNSEEN"}

    nested = tmp_path / "nested.json"
    nested.write_text(
        json.dumps({"groups": {"variant": ["id-1", "id-2"], "SEEN": ["id-3"]}}),
        encoding="utf-8",
    )
    assert read_group_map(nested) == {
        "id-1": "VARIANT",
        "id-2": "VARIANT",
        "id-3": "SEEN",
    }


def test_rows_without_cases_can_still_be_grouped_by_an_explicit_map():
    rows = [{"case_id": "c#0", "scenario_id": "SCENE_X", "sample_id": "s0"}]
    assert groups_from_rows(rows)["c#0"] == UNLABELED
    assert groups_from_rows(rows, {"SCENE_X": "UNSEEN"})["c#0"] == "UNSEEN"


def _record(kind: str, scenario: str, text: str, plan: str, index: int = 0) -> dict:
    return {
        "metadata": {"scenario_id": scenario},
        "model_request": {
            "source_text": text,
            "request_id": f"{kind}-{index}",
            "command_id": f"{kind}-{index}",
        },
        "teacher_plan": {
            "steps": [{"behavior": plan, "target": {"target_id": None}}]
        },
    }


def test_lookup_probe_reports_both_hits_and_agreement():
    train = [
        _record("tr", "SCENE_A", "keep lane", "FOLLOW", 0),
        _record("tr", "SCENE_A", "keep lane", "FOLLOW", 1),
        _record("tr", "SCENE_B", "slow down", "SLOW_DOWN", 2),
    ]
    validation = [
        _record("va", "SCENE_A", "keep lane", "FOLLOW", 0),      # key found, agrees
        _record("va", "SCENE_B", "slow down", "SLOW_DOWN", 1),   # key found, agrees
        _record("va", "SCENE_C", "turn left", "TURN", 2),        # key missing
    ]
    report = lookup_probe(train, validation)
    assert report["train_cases"] == 3
    assert report["validation_cases"] == 3
    assert report["instruction_text_in_train"] == 2
    assert report["scenario_id_in_train"] == 2
    assert report["lookup_key_found"] == 2
    assert report["lookup_recalls_teacher_plan"] == 2
    assert report["validation_distinct_instruction_texts"] == 3
    assert report["verdict"] in {"LOOKUP_SHORTCUT_PRESENT", "NO_LOOKUP_SHORTCUT_FOUND"}


def test_lookup_probe_detects_a_verbatim_copy_of_the_validation_plan():
    train = [_record("tr", "S", "keep lane", "FOLLOW", index) for index in range(4)]
    validation = [_record("va", "S", "keep lane", "FOLLOW", index) for index in range(4)]
    report = lookup_probe(train, validation)
    assert report["lookup_recalls_teacher_plan_share"] == 1.0
    assert report["verdict"] == "LOOKUP_SHORTCUT_PRESENT"
    assert report["validation_cases_per_distinct_instruction_text"] == 4.0

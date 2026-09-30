import json

from challenge.distillation.final_slice_eval import (
    _percentile,
    audit_dataset_coverage,
)


def _record(*behaviors: str) -> dict:
    return {
        "sample_id": "sample-" + "-".join(behaviors),
        "teacher_plan": {
            "steps": [{"behavior": behavior} for behavior in behaviors],
        },
    }


def _write_jsonl(path, records) -> None:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_dataset_coverage_reports_missing_lengths_without_claiming_pass(tmp_path):
    train = tmp_path / "train.jsonl"
    val = tmp_path / "val.jsonl"
    _write_jsonl(train, [_record("TURN_LEFT"), _record("YIELD", "PULL_OVER")])
    _write_jsonl(val, [_record("TURN_LEFT")])

    report = audit_dataset_coverage({"train_path": str(train), "val_path": str(val)})

    assert report["status"] == "MISSING_REQUIRED_COVERAGE"
    assert report["missing_required_plan_lengths"] == [3, 4]
    assert report["missing_required_behaviors"] == []
    assert report["combined"]["plan_length_sample_counts"] == {
        "1": 2,
        "2": 1,
        "3": 0,
        "4": 0,
    }


def test_nearest_rank_percentile_is_deterministic():
    assert _percentile([4.0, 1.0, 3.0, 2.0], 0.95) == 4.0
    assert _percentile([], 0.95) is None

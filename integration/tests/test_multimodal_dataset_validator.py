import json
from pathlib import Path

from tools.validate_multimodal_dataset import validate_dataset


ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "datasets" / "multimodal_v1" / "examples" / "sample.jsonl"


def test_checked_in_sample_is_valid():
    assert validate_dataset(SAMPLE) == []


def test_duplicate_sample_and_split_leak_are_rejected(tmp_path):
    record = json.loads(SAMPLE.read_text(encoding="utf-8"))
    second = dict(record)
    second["split"] = "test"
    target = tmp_path / "records.jsonl"
    target.write_text(
        json.dumps(record, ensure_ascii=False)
        + "\n"
        + json.dumps(second, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    errors = validate_dataset(target)
    assert any("duplicate sample_id" in error for error in errors)
    assert any("leaks across" in error for error in errors)


def test_unsafe_media_paths_are_rejected(tmp_path):
    record = json.loads(SAMPLE.read_text(encoding="utf-8"))
    record["sensors"]["rgb_front"]["path"] = "../outside.jpg"
    target = tmp_path / "records.jsonl"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    assert any("safe relative path" in error for error in validate_dataset(target))

    record["sensors"]["rgb_front"]["path"] = "C:/outside.jpg"
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    assert any("safe relative path" in error for error in validate_dataset(target))

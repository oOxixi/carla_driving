from copy import deepcopy
import json
from pathlib import Path

from challenge.distillation.dataset import build_mock_records
from challenge.distillation.preflight import preflight_datasets


def _write(path: Path, records: list[dict], split: str, version: str = "b1-v1") -> None:
    rows = []
    for record in records:
        copied = deepcopy(record)
        copied["metadata"]["split"] = split
        copied["metadata"]["dataset_version"] = version
        rows.append(json.dumps(copied, ensure_ascii=False))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_preflight_accepts_valid_disjoint_train_validation(tmp_path: Path) -> None:
    records = build_mock_records(8)
    train_path, val_path = tmp_path / "train.jsonl", tmp_path / "validation.jsonl"
    _write(train_path, records[:6], "train")
    _write(val_path, records[6:], "validation")

    report = preflight_datasets(
        train_path, val_path, expected_version="b1-v1",
    )

    assert report["valid"] is True
    assert report["error_count"] == 0
    assert report["train"]["valid_records"] == 6
    assert report["validation"]["valid_records"] == 2
    assert report["train"]["behaviors"]["KEEP_LANE"] >= 1


def test_preflight_rejects_cross_split_overlap_and_frozen_metadata(tmp_path: Path) -> None:
    records = build_mock_records(4)
    train_path, val_path = tmp_path / "train.jsonl", tmp_path / "validation.jsonl"
    _write(train_path, records[:3], "train")
    _write(val_path, [records[1], records[3]], "validation")
    # Preserve overlap identities while making split provenance superficially valid.
    rows = [json.loads(line) for line in val_path.read_text(encoding="utf-8").splitlines()]
    rows[1]["metadata"]["split"] = "frozen_test"
    val_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8",
    )

    report = preflight_datasets(
        train_path, val_path, expected_version="b1-v1",
    )

    assert report["valid"] is False
    codes = {error["code"] for error in report["errors"]}
    assert "CROSS_SPLIT_OVERLAP" in codes
    assert "INVALID_RECORD" in codes

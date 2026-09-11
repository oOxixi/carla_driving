from copy import deepcopy
import json
from pathlib import Path

from challenge.distillation.dataset import build_mock_records
from challenge.distillation.preflight import preflight_datasets


TEACHER_SHA = "a05c8b76efcd4c176965223c661f40b153cb1836"
TEACHER_MODEL = "Qwen/Qwen3.5-2B"
TEACHER_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
TEACHER_FINGERPRINT = (
    "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
)


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


def test_preflight_enforces_pinned_teacher_provenance(tmp_path: Path) -> None:
    records = build_mock_records(6)
    for index, record in enumerate(records):
        if index < 4:
            record["metadata"].update({
                "teacher_git_sha": TEACHER_SHA,
                "teacher_model_id": TEACHER_MODEL,
                "teacher_model_revision": TEACHER_REVISION,
                "teacher_artifact_fingerprint_sha256": TEACHER_FINGERPRINT,
            })
        else:
            # Formal B1 D1 uses explicit baseline and model-artifact names and
            # preserves the collection SHA in the historical ambiguous field.
            record["metadata"].update({
                "teacher_git_sha": "f" * 40,
                "teacher_baseline_git_sha": TEACHER_SHA,
                "teacher_model_id": TEACHER_MODEL,
                "teacher_model_revision": TEACHER_REVISION,
                "teacher_model_artifact_sha256": TEACHER_FINGERPRINT,
            })
    train_path, val_path = tmp_path / "train.jsonl", tmp_path / "validation.jsonl"
    _write(train_path, records[:4], "train")
    _write(val_path, records[4:], "validation")

    expected = {
        "expected_version": "b1-v1",
        "expected_teacher_git_sha": TEACHER_SHA,
        "expected_teacher_model_id": TEACHER_MODEL,
        "expected_teacher_model_revision": TEACHER_REVISION,
        "expected_teacher_artifact_fingerprint_sha256": TEACHER_FINGERPRINT,
    }
    report = preflight_datasets(train_path, val_path, **expected)

    assert report["valid"] is True
    assert report["expected_teacher_identity"]["model_revision"] == TEACHER_REVISION
    assert (
        report["expected_teacher_identity"]["artifact_fingerprint_sha256"]
        == TEACHER_FINGERPRINT
    )

    rows = [json.loads(line) for line in val_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["metadata"]["teacher_model_artifact_sha256"] = "0" * 64
    val_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8",
    )
    rejected = preflight_datasets(train_path, val_path, **expected)

    assert rejected["valid"] is False
    assert any(
        "artifact_fingerprint_sha256 does not match" in error["message"]
        for error in rejected["errors"]
    )

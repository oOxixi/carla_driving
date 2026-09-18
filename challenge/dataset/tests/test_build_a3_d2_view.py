from __future__ import annotations

import json
from pathlib import Path

import pytest

from challenge.dataset.build_a3_d2_view import _cohort_identity, build_view


REPO = Path(__file__).resolve().parents[3]
RELEASE = REPO / "challenge" / "dataset" / "releases" / "d2_v1_1"


def test_build_view_preserves_source_and_excludes_non_success(tmp_path: Path) -> None:
    report = build_view(RELEASE, tmp_path)
    assert report["counts"] == {"train": 2332, "val": 489, "excluded": 231}
    assert report["exclusion_reasons"]["train:B1_HARD_NEGATIVE"] == 143
    assert report["exclusion_reasons"]["val:B1_HARD_NEGATIVE"] == 31
    assert report["exclusion_reasons"]["train:A3_STRICT_TERMINAL_NON_SUCCESS"] == 38
    assert report["exclusion_reasons"]["val:A3_STRICT_TERMINAL_NON_SUCCESS"] == 19
    train = json.loads((tmp_path / "train.jsonl").open(encoding="utf-8").readline())
    assert train["metadata"]["source_dataset_version"] == train["dataset_version"]
    assert train["metadata"]["split"] == "train"
    assert train["metadata"]["teacher_provenance_manifest_sha256"]


def test_cohort_gate_rejects_wrong_teacher_sha() -> None:
    row = json.loads((RELEASE / "train.jsonl").open(encoding="utf-8").readline())
    row["metadata"]["teacher_git_sha"] = "0" * 40
    with pytest.raises(ValueError, match="collection Teacher SHA mismatch"):
        _cohort_identity(REPO, row)

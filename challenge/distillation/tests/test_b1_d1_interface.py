from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from challenge.dataset import collect_d1_200
from challenge.dataset.collect_d1_200 import (
    load_model_artifact_manifest,
    student_view_or_reason,
)
from challenge.distillation.dataset import load_jsonl


ROOT = Path(__file__).resolve().parents[3]
SMOKE_SAMPLE = (
    ROOT / "challenge" / "dataset" / "smoke_v0" / "data" / "smoke_valid.jsonl"
)


def _sample() -> dict:
    sample = deepcopy(load_jsonl(SMOKE_SAMPLE)[0])
    sample["quality"]["valid_for_training"] = True
    sample["closed_loop_quality"].update({
        "available": True,
        "command_terminal_status": "SUCCEEDED",
        "plan_terminal_state": "SUCCEEDED",
    })
    return sample


def test_d1_student_view_requires_successful_closed_loop() -> None:
    view, reason = student_view_or_reason(_sample())

    assert reason is None
    assert view is not None
    assert view["quality"]["schema_valid"] is True
    assert view["quality"]["closed_loop_success"] is True
    assert view["training_policy"]["train_eligible"] is True

    failed = _sample()
    failed["closed_loop_quality"]["plan_terminal_state"] = "FAILED"
    view, reason = student_view_or_reason(failed)

    assert view is None
    assert reason == "PLAN_TERMINAL_NOT_SUCCEEDED"


def test_d1_student_view_rejects_missing_closed_loop_evidence() -> None:
    sample = _sample()
    sample["closed_loop_quality"]["available"] = False

    view, reason = student_view_or_reason(sample)

    assert view is None
    assert reason == "CLOSED_LOOP_EVIDENCE_MISSING"


def test_d1_artifact_manifest_is_verified_not_only_declared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = [{"path": "weights.bin", "size_bytes": 3, "sha256": "1" * 64}]
    fingerprint = hashlib.sha256(
        json.dumps(
            files, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    monkeypatch.setattr(collect_d1_200, "EXPECTED_ARTIFACT_SHA256", fingerprint)
    manifest = {
        "model_id": collect_d1_200.EXPECTED_MODEL_ID,
        "model_revision": collect_d1_200.EXPECTED_MODEL_REVISION,
        "model_artifact_sha256": fingerprint,
        "file_count": 1,
        "fingerprint_method": "test",
        "files": files,
    }
    path = tmp_path / "teacher_model_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    evidence = load_model_artifact_manifest(path)
    assert evidence["model_artifact_sha256"] == fingerprint

    manifest["files"][0]["size_bytes"] = 4
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match pinned artifact"):
        load_model_artifact_manifest(path)

from __future__ import annotations

import json
from pathlib import Path

from CARLA_Language_Benchmark.tools.audit_global_benchmark_v1 import audit_dataset


ROOT = Path(__file__).resolve().parents[2]


def test_language_benchmark_is_frozen_and_repairable() -> None:
    benchmark = ROOT / "CARLA-Language-Benchmark"
    data_path = benchmark / "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json"
    card_path = benchmark / "dataset_card.json"
    checksum_path = benchmark / "baseline/freeze_p0/dataset_checksum.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))
    card = json.loads(card_path.read_text(encoding="utf-8"))
    checksum = json.loads(checksum_path.read_text(encoding="utf-8"))
    report = audit_dataset(data_path)

    assert card["release_status"] == "frozen_baseline"
    assert card["total_records"] == len(rows) == 6192
    assert len({row["id"] for row in rows}) == 6192
    assert all(row["expected_action"] for row in rows)
    assert report["errors"] == 0
    assert checksum["path"] == "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json"
    assert checksum["records"] == 6192
    assert checksum["sha256"] == report["sha256"]


def test_language_benchmark_does_not_claim_unauditable_accuracy() -> None:
    benchmark = ROOT / "CARLA-Language-Benchmark"
    freeze = benchmark / "baseline/freeze_p0"
    data_path = benchmark / "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json"
    policy = json.loads((freeze / "metric_policy.json").read_text(encoding="utf-8"))
    report = audit_dataset(data_path)

    assert not (freeze / "freeze_report.json").exists()
    assert not (freeze / "baseline_manifest.json").exists()
    assert not (freeze / "checksum.json").exists()
    assert policy["evaluation"]["benchmark_role"] == "language_schema_regression_only"
    assert policy["evaluation"]["formal_accuracy"] == {
        "status": "not_yet_frozen",
        "artifact_path": "datasets/formal_validation/CARLA_multimodal_validation_v1.json",
        "required_fields": ["split_id", "record_ids", "records", "sha256"],
        "accuracy_reporting_permitted": False,
    }
    assert report["evaluation_contract"] == "language_schema_regression_only"
    assert report["errors"] == 0

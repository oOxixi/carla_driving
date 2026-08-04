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

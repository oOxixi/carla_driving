from __future__ import annotations

import json
from pathlib import Path

import pytest

from integration.run_manifest import begin_run, finish_run
from tools.run_four_modal_full_chain import main


def test_failed_run_keeps_logs_and_atomic_final_status(tmp_path: Path) -> None:
    context = begin_run(
        tmp_path,
        {
            "git_commit": "05281a8",
            "profile": "qwen3vl-2b-int4",
            "dataset_sha256": "a" * 64,
            "seed": 20260804,
        },
    )
    (context.logs_dir / "qwen_server.log").write_text(
        "startup failed", encoding="utf-8"
    )

    finish_run(context, "FAILED", "qwen_not_ready")

    manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["failure_reason"] == "qwen_not_ready"
    assert (context.logs_dir / "qwen_server.log").exists()
    assert not context.manifest_path.with_suffix(".json.tmp").exists()


def test_invalid_evaluator_input_still_finishes_a_failed_run(
    tmp_path: Path, monkeypatch
) -> None:
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_four_modal_full_chain.py",
            "--qwen-base-url", "http://fake.invalid/v1",
            "--asr-manifest", str(missing),
            "--multimodal-cases", str(missing),
            "--latency-manifest", str(missing),
            "--output", str(tmp_path / "report.json"),
        ],
    )

    with pytest.raises(FileNotFoundError):
        main()

    manifest_path = next((tmp_path / "runs").glob("*/run_manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert (manifest_path.parent / "logs").is_dir()
    assert (manifest_path.parent / "metrics" / "raw_timings.jsonl").is_file()


def test_non_official_measurement_count_requires_diagnostic_marker(
    tmp_path: Path, monkeypatch
) -> None:
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_four_modal_full_chain.py",
            "--qwen-base-url", "http://fake.invalid/v1",
            "--asr-manifest", str(missing),
            "--multimodal-cases", str(missing),
            "--latency-manifest", str(missing),
            "--warmup", "0",
            "--measured", "1",
            "--output", str(tmp_path / "report.json"),
        ],
    )

    with pytest.raises(ValueError, match="official evidence requires"):
        main()

    manifest_path = next((tmp_path / "runs").glob("*/run_manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["diagnostic"] is False

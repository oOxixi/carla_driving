"""Prepare the official Group 1 voice dataset for task 5/6 evaluation.

The input archive is kept out of git, while this script writes lightweight
manifests and audit reports that can be committed and uploaded with the code.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import posixpath
import subprocess
import zipfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "data_short.zip"
DEFAULT_EXTRACT_ROOT = ROOT / "data" / "group1_voice"
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts" / "group1_voice"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_state() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else "unknown",
        "dirty": bool(status.stdout.strip()),
        "status": [line for line in status.stdout.splitlines() if line.strip()],
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _archive_member_count(zip_path: Path, suffix: str) -> int:
    with zipfile.ZipFile(zip_path) as archive:
        return sum(name.endswith(suffix) for name in archive.namelist())


def _extract_if_needed(zip_path: Path, extract_root: Path) -> Path:
    dataset_root = extract_root / "data_short"
    required_files = (
        dataset_root / "mapping.json",
        dataset_root / "mapping_noisy.json",
        dataset_root / "train.json",
        dataset_root / "test.json",
    )
    if all(path.is_file() for path in required_files):
        return dataset_root
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_root)
    return dataset_root


def _normalize_archive_path(value: str) -> str:
    return posixpath.normpath(value.replace("\\", "/"))


def _audio_entries(record: dict[str, Any], condition: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    mandarin = record.get("mandarin") or {}
    if mandarin.get("audio"):
        entries.append(
            {
                "language": "普通话",
                "voice": mandarin.get("voice"),
                "audio": _normalize_archive_path(mandarin["audio"]),
                "condition": condition,
            }
        )
    for dialect in record.get("dialects") or []:
        if dialect.get("audio"):
            entries.append(
                {
                    "language": dialect.get("dialect_name", "方言"),
                    "voice": dialect.get("voice"),
                    "audio": _normalize_archive_path(dialect["audio"]),
                    "condition": condition,
                }
            )
    return entries


def _build_manifest(
    records: list[dict[str, Any]],
    *,
    condition: str,
    audio_prefix: str,
    dataset_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for record in records:
        for index, audio in enumerate(_audio_entries(record, condition), start=1):
            rel_audio = _normalize_archive_path(audio["audio"])
            if audio_prefix:
                rel_audio = posixpath.join(audio_prefix, rel_audio)
            item = {
                "id": f"{record['id']}__{condition}__{index}",
                "source_id": record["id"],
                "lang": audio["language"],
                "voice": audio["voice"],
                "audio": rel_audio,
                "text": record["text"],
                "intent": record.get("intent", "UNKNOWN"),
                "slots": record.get("slots") or {},
                "scene_type": record.get("scene_type", "unknown"),
                "condition": condition,
            }
            manifest.append(item)
            if not (dataset_root / rel_audio).is_file():
                missing.append(
                    {
                        "id": item["id"],
                        "source_id": item["source_id"],
                        "audio": rel_audio,
                    }
                )
    return manifest, missing


def _counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0]))


def _manifest_stats(manifest: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "entries": len(manifest),
        "unique_texts": len({item["text"] for item in manifest}),
        "unique_source_ids": len({item["source_id"] for item in manifest}),
        "by_language": _counter_to_dict(Counter(item["lang"] for item in manifest)),
        "by_intent": _counter_to_dict(Counter(item["intent"] for item in manifest)),
        "by_scene_type": _counter_to_dict(
            Counter(item["scene_type"] for item in manifest)
        ),
    }


def _duplicate_texts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        grouped[record["text"]].append(record["id"])
    return [
        {"text": text, "ids": ids, "count": len(ids)}
        for text, ids in sorted(grouped.items())
        if len(ids) > 1
    ]


def _label_conflicts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for record in records:
        signature = json.dumps(
            {
                "intent": record.get("intent"),
                "slots": record.get("slots") or {},
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        grouped[record["text"]].add(signature)
    return [
        {"text": text, "labels": sorted(labels), "count": len(labels)}
        for text, labels in sorted(grouped.items())
        if len(labels) > 1
    ]


def _split_stats(dataset_root: Path) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    split_texts: dict[str, set[str]] = {}
    for name in ("train", "test"):
        path = dataset_root / f"{name}.json"
        if not path.is_file():
            continue
        data = _load_json(path)
        stats[name] = {
            "records": len(data),
            "unique_texts": len({item.get("text", "") for item in data}),
            "by_intent": _counter_to_dict(Counter(item.get("intent") for item in data)),
        }
        split_texts[name] = {item.get("text", "") for item in data}
    leakage = sorted(split_texts.get("train", set()) & split_texts.get("test", set()))
    stats["train_test_text_overlap"] = {
        "count": len(leakage),
        "examples": leakage[:20],
    }
    return stats


def _markdown_report(audit: dict[str, Any]) -> str:
    clean = audit["manifests"]["clean"]
    noisy = audit["manifests"]["noise_50dba"]
    lines = [
        "# Group 1 Task 5/6 Voice Dataset Preparation",
        "",
        f"- Generated UTC: `{audit['generated_at_utc']}`",
        f"- Source zip: `{audit['source_zip']['path']}`",
        f"- Source zip SHA256: `{audit['source_zip']['sha256']}`",
        f"- Extracted root: `{audit['dataset_root']}`",
        f"- Git commit: `{audit['git']['commit']}`",
        f"- Official-for-evaluation flag: `{audit['official_for_group1_tasks']}`",
        "",
        "## Manifest Counts",
        "",
        "| Condition | Entries | Unique texts | Unique source ids | Missing audio |",
        "|---|---:|---:|---:|---:|",
        (
            f"| clean | {clean['stats']['entries']} | {clean['stats']['unique_texts']} | "
            f"{clean['stats']['unique_source_ids']} | {clean['missing_audio_count']} |"
        ),
        (
            f"| noise_50dba | {noisy['stats']['entries']} | {noisy['stats']['unique_texts']} | "
            f"{noisy['stats']['unique_source_ids']} | {noisy['missing_audio_count']} |"
        ),
        "",
        "## Task Mapping",
        "",
        "- Task 5 uses the generated manifests with `tools/evaluate_voice_audio.py` for real ASR, and `tools/run_group1_voice_text_regression.py` for deterministic text/intent/slot/safety gates.",
        "- Task 6 uses the same manifests with `tools/run_group1_voice_fastpath_benchmark.py` to measure NLU fast-path latency and second-model trigger policy before full ASR benchmarking.",
        "- The noisy manifest is marked `noise_50dba` because this archive is being treated as the official Group 1 audio drop for this workspace.",
        "",
        "## Follow-up Commands",
        "",
        "```bash",
        "python3 tools/run_group1_voice_text_regression.py \\",
        "  --manifest artifacts/group1_voice/manifests/data_short_clean_manifest.json \\",
        "  --output artifacts/group1_voice/task5_text_regression_clean.json",
        "",
        "python3 tools/run_group1_voice_fastpath_benchmark.py \\",
        "  --manifest artifacts/group1_voice/manifests/data_short_clean_manifest.json \\",
        "  --output artifacts/group1_voice/task6_fastpath_clean.json",
        "",
        "python3 tools/evaluate_voice_audio.py \\",
        "  --manifest artifacts/group1_voice/manifests/data_short_clean_manifest.json \\",
        "  --audio-root data/group1_voice/data_short \\",
        "  --condition clean \\",
        "  --output artifacts/group1_voice/task5_asr_clean.json \\",
        "  --min-intent-accuracy 0.98",
        "",
        "python3 tools/evaluate_voice_audio.py \\",
        "  --manifest artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json \\",
        "  --audio-root data/group1_voice/data_short \\",
        "  --condition noise_50dba \\",
        "  --noise-level-dba 50.0 \\",
        "  --calibration-log artifacts/group1_voice/calibration/data_short_50dba_calibration.json \\",
        "  --output artifacts/group1_voice/task5_asr_noise_50dba.json \\",
        "  --min-intent-accuracy 0.98",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip-path", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--extract-root", type=Path, default=DEFAULT_EXTRACT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--official-for-group1-tasks",
        action="store_true",
        default=True,
        help="Mark this archive as the official Group 1 audio drop in reports.",
    )
    args = parser.parse_args()

    zip_path = args.zip_path.resolve()
    if not zip_path.is_file():
        parser.error(f"missing zip archive: {zip_path}")

    dataset_root = _extract_if_needed(zip_path, args.extract_root.resolve())
    output_root = args.output_root.resolve()
    manifests_dir = output_root / "manifests"
    calibration_dir = output_root / "calibration"

    clean_records = _load_json(dataset_root / "mapping.json")
    noisy_records = _load_json(dataset_root / "mapping_noisy.json")

    clean_manifest, clean_missing = _build_manifest(
        clean_records,
        condition="clean",
        audio_prefix="",
        dataset_root=dataset_root,
    )
    noisy_manifest, noisy_missing = _build_manifest(
        noisy_records,
        condition="noise_50dba",
        audio_prefix="",
        dataset_root=dataset_root,
    )

    clean_manifest_path = manifests_dir / "data_short_clean_manifest.json"
    noisy_manifest_path = manifests_dir / "data_short_noisy_50dba_manifest.json"
    _write_json(clean_manifest_path, clean_manifest)
    _write_json(noisy_manifest_path, noisy_manifest)

    source_zip = {
        "path": str(zip_path),
        "sha256": _sha256(zip_path),
        "size_bytes": zip_path.stat().st_size,
        "mp3_members": _archive_member_count(zip_path, ".mp3"),
        "wav_members": _archive_member_count(zip_path, ".wav"),
    }
    calibration = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_zip_sha256": source_zip["sha256"],
        "dataset": "data_short",
        "condition": "noise_50dba",
        "noise_level_dba": 50.0,
        "calibration_source": "accepted_official_group1_audio_drop",
        "official_for_group1_tasks": args.official_for_group1_tasks,
        "notes": [
            "This file records the workspace decision to evaluate the noisy split as the official 50 dBA condition.",
            "Use an external sound-level-meter log here if the team later replaces this archive with newly measured recordings.",
        ],
    }
    calibration_path = calibration_dir / "data_short_50dba_calibration.json"
    _write_json(calibration_path, calibration)

    audit = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_for_group1_tasks": args.official_for_group1_tasks,
        "dataset_root": str(dataset_root),
        "source_zip": source_zip,
        "git": _git_state(),
        "raw_records": {
            "clean_mapping": len(clean_records),
            "noisy_mapping": len(noisy_records),
            "duplicate_texts": _duplicate_texts(clean_records)[:50],
            "duplicate_text_count": len(_duplicate_texts(clean_records)),
            "label_conflicts": _label_conflicts(clean_records),
            "split_stats": _split_stats(dataset_root),
        },
        "manifests": {
            "clean": {
                "path": str(clean_manifest_path),
                "stats": _manifest_stats(clean_manifest),
                "missing_audio_count": len(clean_missing),
                "missing_audio_examples": clean_missing[:20],
            },
            "noise_50dba": {
                "path": str(noisy_manifest_path),
                "stats": _manifest_stats(noisy_manifest),
                "missing_audio_count": len(noisy_missing),
                "missing_audio_examples": noisy_missing[:20],
            },
        },
        "calibration_log": str(calibration_path),
    }
    audit_path = output_root / "data_short_dataset_audit.json"
    _write_json(audit_path, audit)
    (output_root / "GROUP1_TASK5_6_DATASET_PREP.md").write_text(
        _markdown_report(audit),
        encoding="utf-8",
    )

    print(f"dataset_root={dataset_root}")
    print(f"clean_manifest={clean_manifest_path} entries={len(clean_manifest)} missing={len(clean_missing)}")
    print(f"noisy_manifest={noisy_manifest_path} entries={len(noisy_manifest)} missing={len(noisy_missing)}")
    print(f"audit={audit_path}")
    print(f"calibration_log={calibration_path}")
    return 0 if not clean_missing and not noisy_missing else 2


if __name__ == "__main__":
    raise SystemExit(main())

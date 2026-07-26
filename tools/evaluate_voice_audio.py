"""Run the complete voice pipeline over a manifest and write audit evidence.

This tool performs real ASR inference.  It does not substitute manifest text
for ASR output.  A calibrated 50 dBA dataset is passed with ``--audio-root``;
digital audio files alone cannot prove an absolute sound-pressure level.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import unicodedata
from typing import Any

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[1]
VOICE_ROOT = ROOT / "voice_group"
DEFAULT_MANIFEST = VOICE_ROOT / "test_samples" / "manifest.json"


def _synthetic_noise_audio(
    audio_path: Path,
    snr_db: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Load mono 16 kHz audio and add deterministic white noise at an SNR.

    SNR is a digital signal ratio.  It is deliberately not described as dBA,
    which requires calibrated acoustic playback and measurement.
    """
    waveform, sample_rate = sf.read(audio_path, dtype="float32")
    waveform = np.asarray(waveform, dtype=np.float32)
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)
    if sample_rate != 16000:
        output_size = int(len(waveform) * 16000 / sample_rate)
        waveform = np.interp(
            np.linspace(0, len(waveform), output_size, endpoint=False),
            np.arange(len(waveform)),
            waveform,
        ).astype(np.float32)
    signal_rms = max(float(np.sqrt(np.mean(np.square(waveform)))), 1e-6)
    noise_rms = signal_rms / (10.0 ** (snr_db / 20.0))
    noise = rng.normal(0.0, noise_rms, waveform.shape).astype(np.float32)
    return np.clip(waveform + noise, -1.0, 1.0)


def _normalize_transcript(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE)


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return round(ordered[lower], 3)
    fraction = index - lower
    return round(
        ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction,
        3,
    )


def _latency_stats(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean_ms": round(statistics.fmean(values), 3) if values else None,
        "p95_ms": _percentile(values, 0.95),
        "p99_ms": _percentile(values, 0.99),
        "max_ms": round(max(values), 3) if values else None,
    }


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [record for record in records if record.get("inference_ok")]
    reference_chars = sum(record["reference_chars"] for record in valid)
    edit_errors = sum(record["edit_distance"] for record in valid)
    total = len(records)
    return {
        "total": total,
        "inference_success": len(valid),
        "asr_confidence_available": sum(
            record.get("asr_confidence") is not None for record in valid
        ),
        "asr_confidence_coverage": (
            round(
                sum(record.get("asr_confidence") is not None for record in valid)
                / total,
                6,
            )
            if total
            else 0.0
        ),
        "verification_confidence_available": sum(
            record.get("verification_confidence") is not None
            for record in valid
        ),
        "verification_confidence_coverage": (
            round(
                sum(
                    record.get("verification_confidence") is not None
                    for record in valid
                )
                / total,
                6,
            )
            if total
            else 0.0
        ),
        "verification_triggered": sum(
            bool(record.get("asr_verification")) for record in valid
        ),
        "verification_semantic_agreement": sum(
            (record.get("asr_verification") or {}).get("semantic_agreement")
            is True
            for record in valid
        ),
        "verification_confirmation_gates": sum(
            bool(record.get("confirm_required")) for record in valid
        ),
        "verification_disagreement_gates": sum(
            record.get("ambiguity_type") == "ASR_MODEL_DISAGREEMENT"
            for record in valid
        ),
        "asr_exact_accuracy": (
            round(sum(record["asr_exact"] for record in valid) / total, 6)
            if total
            else 0.0
        ),
        "asr_character_accuracy": (
            round(max(0.0, 1.0 - edit_errors / reference_chars), 6)
            if reference_chars
            else 0.0
        ),
        "intent_accuracy": (
            round(sum(record["intent_ok"] for record in valid) / total, 6)
            if total
            else 0.0
        ),
        "slot_accuracy": (
            round(sum(record["slots_ok"] for record in valid) / total, 6)
            if total
            else 0.0
        ),
        "latency": {
            key: _latency_stats(
                [
                    float(record["latency"][key])
                    for record in valid
                    if record.get("latency", {}).get(key) is not None
                ]
            )
            for key in ("asr_ms", "verification_ms", "nlu_ms", "total_ms")
        },
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# 语音真实音频评测报告",
        "",
        f"- 时间（UTC）：`{report['generated_at_utc']}`",
        f"- 条件：`{report['condition']}`",
        f"- Git：`{report['git']['commit']}`",
        f"- 工作区未提交改动：`{report['git']['dirty']}`",
        f"- 音频根目录：`{report['audio_root']}`",
    ]
    calibration = report.get("noise_calibration")
    if calibration:
        lines.extend(
            [
                f"- 环境噪声：`{calibration['level_dba']} dBA`",
                f"- 校准记录：`{calibration['log']}`",
            ]
        )
    lines.extend(
        [
            "",
            "| 语言 | 样本 | ASR 完全匹配 | 字符准确率 | 意图准确率 | 槽位准确率 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for language, metrics in report["by_language"].items():
        lines.append(
            f"| {language} | {metrics['total']} | "
            f"{metrics['asr_exact_accuracy']:.2%} | "
            f"{metrics['asr_character_accuracy']:.2%} | "
            f"{metrics['intent_accuracy']:.2%} | "
            f"{metrics['slot_accuracy']:.2%} |"
        )
    overall = report["overall"]
    lines.extend(
        [
            f"| **总体** | **{overall['total']}** | "
            f"**{overall['asr_exact_accuracy']:.2%}** | "
            f"**{overall['asr_character_accuracy']:.2%}** | "
            f"**{overall['intent_accuracy']:.2%}** | "
            f"**{overall['slot_accuracy']:.2%}** |",
            "",
            f"- SenseVoice 原生置信度覆盖："
            f"`{overall['asr_confidence_coverage']:.2%}`",
            f"- 条件复核置信度覆盖："
            f"`{overall['verification_confidence_coverage']:.2%}` "
            f"（触发 `{overall['verification_triggered']}` 条）",
            f"- 总确认门：`{overall['verification_confirmation_gates']}`；"
            f"模型分歧新增确认门："
            f"`{overall['verification_disagreement_gates']}`",
            "",
            "## 延迟",
            "",
            "| 阶段 | mean | P95 | P99 | max |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for key, label in (
        ("asr_ms", "ASR"),
        ("verification_ms", "条件复核"),
        ("nlu_ms", "NLU"),
        ("total_ms", "端到端"),
    ):
        latency = overall["latency"][key]
        lines.append(
            f"| {label} | {latency['mean_ms']} ms | {latency['p95_ms']} ms | "
            f"{latency['p99_ms']} ms | {latency['max_ms']} ms |"
        )
    lines.extend(
        [
            "",
            f"- 推理异常：`{len(report['inference_errors'])}`",
            f"- 意图失败：`{len(report['intent_failures'])}`",
            "",
        ]
    )
    return "\n".join(lines)


def _git_state() -> dict[str, Any]:
    commit_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status_lines = [
        line for line in status_result.stdout.splitlines() if line.strip()
    ]
    return {
        "commit": (
            commit_result.stdout.strip()
            if commit_result.returncode == 0
            else "unknown"
        ),
        "dirty": bool(status_lines),
        "status": status_lines,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--audio-root",
        type=Path,
        help="Root containing the same relative audio paths as the manifest",
    )
    parser.add_argument(
        "--condition",
        choices=("clean", "noise_50dba", "synthetic_noise"),
        required=True,
    )
    parser.add_argument("--noise-level-dba", type=float)
    parser.add_argument("--calibration-log", type=Path)
    parser.add_argument(
        "--synthetic-snr-db",
        type=float,
        help="Digital white-noise SNR; never evidence of an absolute dBA level",
    )
    parser.add_argument("--noise-seed", type=int, default=20260726)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, help="Smoke-test only; invalid for final evidence")
    parser.add_argument("--min-intent-accuracy", type=float)
    args = parser.parse_args()

    if args.condition == "noise_50dba":
        if args.noise_level_dba is None or abs(args.noise_level_dba - 50.0) > 1.0:
            parser.error("noise_50dba requires --noise-level-dba within 49..51")
        if args.calibration_log is None or not args.calibration_log.is_file():
            parser.error("noise_50dba requires an existing --calibration-log")
    if args.condition == "synthetic_noise" and args.synthetic_snr_db is None:
        parser.error("synthetic_noise requires --synthetic-snr-db")
    if args.condition != "synthetic_noise" and args.synthetic_snr_db is not None:
        parser.error("--synthetic-snr-db is only valid for synthetic_noise")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.limit is not None:
        manifest = manifest[: args.limit]
    audio_root = (args.audio_root or args.manifest.parent).resolve()

    sys.path.insert(0, str(VOICE_ROOT))
    from pipeline import audio_to_command, preload_voice_models

    preload = preload_voice_models()

    records: list[dict[str, Any]] = []
    noise_rng = np.random.default_rng(args.noise_seed)
    for index, item in enumerate(manifest, start=1):
        audio_path = audio_root / item["audio"]
        record: dict[str, Any] = {
            "index": index,
            "language": item["lang"],
            "audio": str(audio_path),
            "reference_text": item["text"],
            "expected_intent": item["intent"],
            "expected_slots": item.get("slots", {}),
        }
        try:
            audio_input: str | np.ndarray = str(audio_path)
            if args.condition == "synthetic_noise":
                audio_input = _synthetic_noise_audio(
                    audio_path,
                    args.synthetic_snr_db,
                    noise_rng,
                )
            command = audio_to_command(audio_input)
            reference = _normalize_transcript(item["text"])
            hypothesis = _normalize_transcript(command["source_text"])
            record.update(
                {
                    "inference_ok": True,
                    "source_text": command["source_text"],
                    "actual_intent": command["intent"],
                    "actual_slots": command.get("parameters", {}),
                    "status": command.get("status"),
                    "confirm_required": command.get("confirm_required", False),
                    "ambiguity_type": command.get("ambiguity_type"),
                    "asr_verification": command.get("asr_verification"),
                    "asr_confidence": command.get("asr_confidence"),
                    "verification_confidence": command.get(
                        "verification_confidence"
                    ),
                    "asr_exact": hypothesis == reference,
                    "reference_chars": len(reference),
                    "edit_distance": _edit_distance(reference, hypothesis),
                    "intent_ok": command["intent"] == item["intent"],
                    "slots_ok": all(
                        command.get("parameters", {}).get(key) == value
                        for key, value in item.get("slots", {}).items()
                    ),
                    "latency": command.get("_latency", {}),
                }
            )
        except Exception as error:
            record.update(
                {
                    "inference_ok": False,
                    "exception": f"{type(error).__name__}: {error}",
                }
            )
        records.append(record)
        print(f"[{index:03d}/{len(manifest):03d}] {item['lang']} {record.get('actual_intent', 'ERROR')}")

    by_language_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_language_records[record["language"]].append(record)
    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "condition": args.condition,
        "manifest": str(args.manifest.resolve()),
        "audio_root": str(audio_root),
        "git": _git_state(),
        "model_preload": preload,
        "sample_limit": args.limit,
        "synthetic_noise": (
            {
                "snr_db": args.synthetic_snr_db,
                "seed": args.noise_seed,
                "official_50dba_evidence": False,
            }
            if args.condition == "synthetic_noise"
            else None
        ),
        "noise_calibration": (
            {
                "level_dba": args.noise_level_dba,
                "log": str(args.calibration_log.resolve()),
            }
            if args.condition == "noise_50dba"
            else None
        ),
        "overall": _summarize(records),
        "by_language": {
            language: _summarize(language_records)
            for language, language_records in sorted(by_language_records.items())
        },
        "inference_errors": [
            record for record in records if not record.get("inference_ok")
        ],
        "intent_failures": [
            record
            for record in records
            if record.get("inference_ok") and not record["intent_ok"]
        ],
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.output.with_suffix(".md").write_text(
        _markdown_report(report),
        encoding="utf-8",
    )

    threshold = args.min_intent_accuracy
    if threshold is None:
        threshold = 0.95 if args.condition == "clean" else 0.90
    passed = (
        report["overall"]["inference_success"] == report["overall"]["total"]
        and report["overall"]["intent_accuracy"] >= threshold
    )
    print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
    print(f"evidence: {args.output} and {args.output.with_suffix('.md')}")
    return 0 if passed else 2


if __name__ == "__main__":
    started = time.monotonic()
    exit_code = main()
    print(f"benchmark wall time: {time.monotonic() - started:.1f}s")
    raise SystemExit(exit_code)

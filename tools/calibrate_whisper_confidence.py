"""Fit and evaluate a provisional faster-whisper confidence calibration.

The bundled manifest contains synthesized speech, so the generated calibration
is useful for engineering tests but is explicitly not official human-speech
evidence.  A deterministic 10 dB SNR variant may be included to expose more
recognition errors than the clean set alone.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
VOICE_ROOT = ROOT / "voice_group"
DEFAULT_MANIFEST = VOICE_ROOT / "test_samples" / "manifest.json"
sys.path.insert(0, str(ROOT))

from tools.evaluate_voice_audio import _synthetic_noise_audio
from voice_group.asr_cascade import CascadeConfig, FasterWhisperVerifier


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE)


def sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-values))


def fit_platt(
    raw_probabilities: list[float],
    labels: list[bool],
    *,
    regularization: float = 1.0,
) -> tuple[float, float]:
    probabilities = np.clip(np.asarray(raw_probabilities), 1e-6, 1 - 1e-6)
    feature = np.log(probabilities / (1.0 - probabilities))
    design = np.column_stack([np.ones_like(feature), feature])
    target = np.asarray(labels, dtype=np.float64)
    coefficients = np.zeros(2, dtype=np.float64)
    penalty = np.diag([0.01, regularization])
    for _ in range(100):
        predictions = sigmoid(design @ coefficients)
        weights = np.maximum(predictions * (1.0 - predictions), 1e-6)
        gradient = design.T @ (target - predictions) - penalty @ coefficients
        information = design.T @ (weights[:, None] * design) + penalty
        update = np.linalg.solve(information, gradient)
        coefficients += update
        if float(np.max(np.abs(update))) < 1e-8:
            break
    return float(coefficients[0]), float(coefficients[1])


def calibrate(
    raw_probability: float,
    intercept: float,
    slope: float,
) -> float:
    value = np.clip(raw_probability, 1e-6, 1 - 1e-6)
    logit = math.log(value / (1.0 - value))
    return float(sigmoid(np.asarray([intercept + slope * logit]))[0])


def metrics(probabilities: list[float], labels: list[bool]) -> dict:
    values = np.asarray(probabilities, dtype=np.float64)
    target = np.asarray(labels, dtype=np.float64)
    return {
        "count": len(labels),
        "correct": int(target.sum()),
        "incorrect": int(len(target) - target.sum()),
        "brier": round(float(np.mean((values - target) ** 2)), 6),
        "mean_probability": round(float(values.mean()), 6),
        "mean_probability_correct": (
            round(float(values[target == 1].mean()), 6)
            if np.any(target == 1)
            else None
        ),
        "mean_probability_incorrect": (
            round(float(values[target == 0].mean()), 6)
            if np.any(target == 0)
            else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="int8_float16")
    parser.add_argument(
        "--languages",
        help="Comma-separated manifest language labels used for calibration",
    )
    parser.add_argument("--include-snr-db", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    samples = json.loads(args.manifest.read_text(encoding="utf-8"))
    selected_languages = None
    if args.languages:
        selected_languages = {
            value.strip()
            for value in args.languages.split(",")
            if value.strip()
        }
        samples = [
            sample
            for sample in samples
            if sample["lang"] in selected_languages
        ]
    if args.limit:
        samples = samples[: args.limit]
    audio_root = args.manifest.parent
    verifier = FasterWhisperVerifier(
        CascadeConfig(
            enabled=True,
            model_size=args.model,
            device=args.device,
            compute_type=args.compute_type,
            calibration_path=Path("__calibration_not_present__.json"),
        )
    )
    rng = np.random.default_rng(args.seed)
    records = []
    conditions: list[tuple[str, float | None]] = [("clean", None)]
    if args.include_snr_db is not None:
        conditions.append(("synthetic_noise", args.include_snr_db))

    for condition, snr_db in conditions:
        for index, sample in enumerate(samples):
            audio_path = audio_root / sample["audio"]
            audio = str(audio_path)
            if snr_db is not None:
                audio = _synthetic_noise_audio(audio_path, snr_db, rng)
            result = verifier.transcribe(audio)
            raw = result["raw_word_probability"]
            if raw is None:
                raise RuntimeError(f"missing word probability for {audio_path}")
            exact = normalize(result["text"]) == normalize(sample["text"])
            record = {
                "sample_index": index,
                "condition": condition,
                "language": sample["lang"],
                "reference": sample["text"],
                "hypothesis": result["text"],
                "exact": exact,
                "raw_word_probability": raw,
                "avg_logprob": result["avg_logprob"],
                "latency_ms": result["latency_ms"],
            }
            records.append(record)
            print(
                f"[{len(records):03d}/{len(samples) * len(conditions):03d}] "
                f"{condition} {sample['lang']} exact={exact} raw={raw:.4f}"
            )

    # Keep all variants of the same utterance in one side of the split.
    train = [record for record in records if record["sample_index"] % 5 != 0]
    validation = [record for record in records if record["sample_index"] % 5 == 0]
    intercept, slope = fit_platt(
        [record["raw_word_probability"] for record in train],
        [record["exact"] for record in train],
    )
    for record in records:
        record["calibrated_confidence"] = round(
            calibrate(record["raw_word_probability"], intercept, slope),
            6,
        )

    train_metrics = metrics(
        [record["calibrated_confidence"] for record in train],
        [record["exact"] for record in train],
    )
    validation_metrics = metrics(
        [record["calibrated_confidence"] for record in validation],
        [record["exact"] for record in validation],
    )
    if validation_metrics["incorrect"] == 0:
        raise RuntimeError(
            "validation split contains no ASR errors; calibration is not auditable"
        )
    if slope <= 0:
        raise RuntimeError(
            "raw word probability does not rank correctness; refusing calibration"
        )

    calibration = {
        "schema_version": "1.0",
        "method": "platt_logit",
        "model": args.model,
        "device_independent": True,
        "intercept": round(intercept, 9),
        "slope": round(slope, 9),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "manifest": str(args.manifest.resolve()),
            "samples": len(samples),
            "languages": sorted(selected_languages) if selected_languages else "all",
            "conditions": [name for name, _ in conditions],
            "synthetic_snr_db": args.include_snr_db,
            "human_recordings": False,
            "official_competition_calibration": False,
            "split": "sample_index modulo 5; variants kept together",
        },
        "train": train_metrics,
        "validation": validation_metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(calibration, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(
            {
                "calibration": calibration,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(calibration, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

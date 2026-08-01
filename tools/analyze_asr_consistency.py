"""Evaluate whether perturbation consistency is usable as ASR confidence.

This is a diagnostic, not a production confidence score.  It compares the
original transcription with a 5 ms time shift and low-amplitude deterministic
Gaussian noise, then reports whether stability separates correct from
incorrect transcriptions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
VOICE_ROOT = ROOT / "voice_group"
MANIFEST = VOICE_ROOT / "test_samples" / "manifest.json"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--noise-ratio", type=float, default=0.02)
    args = parser.parse_args()

    sys.path.insert(0, str(VOICE_ROOT))
    from asr_vad import ASR

    samples = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.limit:
        samples = samples[: args.limit]
    rng = np.random.default_rng(args.seed)
    asr = ASR()
    records = []
    for index, sample in enumerate(samples, start=1):
        path = MANIFEST.parent / sample["audio"]
        waveform = asr._load(str(path))
        rms = max(float(np.sqrt(np.mean(waveform * waveform))), 1e-4)
        shifted = np.concatenate(
            [np.zeros(80, dtype=np.float32), waveform[:-80]]
        )
        noisy = np.clip(
            waveform
            + rng.normal(
                0.0,
                rms * args.noise_ratio,
                waveform.shape,
            ).astype(np.float32),
            -1.0,
            1.0,
        )
        texts = [
            asr.transcribe(variant)["text"]
            for variant in (waveform, shifted, noisy)
        ]
        normalized = [normalize(text) for text in texts]
        exact = normalized[0] == normalize(sample["text"])
        stable = len(set(normalized)) == 1
        records.append(
            {
                "index": index,
                "language": sample["lang"],
                "reference": sample["text"],
                "texts": texts,
                "exact": exact,
                "stable": stable,
            }
        )
        print(index, sample["lang"], exact, stable, texts)

    correct = [record for record in records if record["exact"]]
    incorrect = [record for record in records if not record["exact"]]
    report = {
        "total": len(records),
        "exact": len(correct),
        "incorrect": len(incorrect),
        "stable_total": sum(record["stable"] for record in records),
        "stable_correct": sum(record["stable"] for record in correct),
        "stable_incorrect": sum(record["stable"] for record in incorrect),
        "unstable_correct": sum(not record["stable"] for record in correct),
        "unstable_incorrect": sum(not record["stable"] for record in incorrect),
        "noise_ratio": args.noise_ratio,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

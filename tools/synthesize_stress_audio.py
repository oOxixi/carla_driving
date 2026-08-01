"""Generate deterministic Chinese TTS audio references for full-chain testing.

The generated clips exercise the real ASR model but are not human recordings
and must not be presented as official dialect or 50 dBA evidence.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _synthesize(
    rows: list[dict[str, Any]],
    *,
    dataset_dir: Path,
    voice: str,
    rate: str,
) -> None:
    try:
        import edge_tts
    except ImportError as error:
        raise RuntimeError("install edge-tts before generating stress audio") from error

    audio_dir = dataset_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    by_text: dict[str, tuple[str, str]] = {}
    for row in rows:
        text = str(row["expected_transcript"]).strip()
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        filename = f"{key}.mp3"
        destination = audio_dir / filename
        if text not in by_text:
            if not destination.exists():
                await edge_tts.Communicate(
                    text,
                    voice=voice,
                    rate=rate,
                ).save(str(destination))
            by_text[text] = (f"audio/{filename}", _sha256(destination))
        audio_ref, audio_sha256 = by_text[text]
        row["audio_ref"] = audio_ref
        row["audio_sha256"] = audio_sha256
        row.setdefault("provenance", {})["audio"] = {
            "kind": "edge_tts_synthetic",
            "voice": voice,
            "rate": rate,
            "sha256": audio_sha256,
            "eligible_for_50dba_claim": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument(
        "--cases-file",
        type=Path,
        default=Path("cases.jsonl"),
        help="JSONL path relative to dataset_dir.",
    )
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+0%")
    args = parser.parse_args()
    dataset_dir = args.dataset_dir.resolve()
    cases_path = args.cases_file
    if not cases_path.is_absolute():
        cases_path = dataset_dir / cases_path
    rows = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    asyncio.run(
        _synthesize(
            rows,
            dataset_dir=dataset_dir,
            voice=args.voice,
            rate=args.rate,
        )
    )
    cases_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    report = {
        "case_count": len(rows),
        "unique_audio_count": len({row["audio_ref"] for row in rows}),
        "voice": args.voice,
        "rate": args.rate,
        "kind": "synthetic_tts_for_real_asr_regression",
        "eligible_for_50dba_claim": False,
    }
    report_path = cases_path.with_suffix(".audio_report.json")
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Benchmark the exported SenseVoice ONNX model on Group 1 voice data."""

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
import onnxruntime as ort
import soundfile as sf
import torch
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT / "artifacts" / "group1_voice" / "manifests" / "data_short_clean_manifest.json"
)
DEFAULT_AUDIO_ROOT = ROOT / "data" / "group1_voice" / "data_short"
DEFAULT_MODEL = ROOT / "artifacts" / "group1_voice" / "onnx_export" / "sensevoice_legacy" / "model.onnx"
DEFAULT_OUTPUT = ROOT / "artifacts" / "group1_voice" / "task6_onnx_clean_limit50.json"
TOKENS_PATH = Path.home() / ".cache" / "modelscope" / "hub" / "iic" / "SenseVoiceSmall" / "tokens.json"
SENSEVOICE_PATH = Path.home() / ".cache" / "modelscope" / "hub" / "iic" / "SenseVoiceSmall"


_EMOJI = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2190-\u21FF\u2B00-\u2BFF]")
_TAG = re.compile(r"<\|[^|]*\|>")
_CORRECTION = {"施工去": "施工区", "考边停车": "靠边停车", "掉投": "掉头"}
_LANGUAGE_IDS = {"zh": 0, "en": 3, "yue": 7, "ja": 11, "ko": 12}
_TEXTNORM_IDS = {"with_itn": 14, "without_itn": 15}


sys.path.insert(0, str(ROOT))
from voice_group.nlu_b2.parser import parse_command  # noqa: E402
from voice_group.vehicle_nlu.src.b1_service import process_asr_text  # noqa: E402


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


def _slots_match(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Match annotated slots without rejecting additional executable metadata."""

    return all(actual.get(key) == value for key, value in expected.items())


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
    return round(ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction, 3)


def _latency_stats(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean_ms": round(statistics.fmean(values), 3) if values else None,
        "p95_ms": _percentile(values, 0.95),
        "p99_ms": _percentile(values, 0.99),
        "max_ms": round(max(values), 3) if values else None,
    }


def _strip_and_correct(text: str) -> str:
    text = _TAG.sub("", text)
    text = _EMOJI.sub("", text).strip()
    for wrong, right in _CORRECTION.items():
        text = text.replace(wrong, right)
    return text


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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    overall = report["overall"]
    lines = [
        "# Group 1 Task 6 ONNX Benchmark",
        "",
        f"- Generated UTC: `{report['generated_at_utc']}`",
        f"- Manifest: `{report['manifest']}`",
        f"- ONNX model: `{report['onnx_model']}`",
        f"- Provider: `{report['provider']}`",
        f"- Samples: `{overall['total']}`",
        f"- ASR exact accuracy: `{overall['asr_exact_accuracy']:.2%}`",
        f"- Intent accuracy: `{overall['intent_accuracy']:.2%}`",
        f"- Slot accuracy: `{overall['slot_accuracy']:.2%}`",
        "",
        "| Stage | mean | P95 | P99 | max |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, label in (
        ("frontend_ms", "Frontend"),
        ("onnx_ms", "ONNX"),
        ("nlu_ms", "NLU"),
        ("model_nlu_ms", "ONNX+NLU"),
        ("total_ms", "End-to-end"),
    ):
        latency = overall["latency"][key]
        lines.append(
            f"| {label} | {latency['mean_ms']} ms | {latency['p95_ms']} ms | "
            f"{latency['p99_ms']} ms | {latency['max_ms']} ms |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Transcript decoding uses greedy CTC collapse plus SenseVoice tag postprocess.",
            "- Frontend uses the same FunASR WavFrontend configuration as the PyTorch baseline.",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class OnnxSenseVoice:
    def __init__(
        self, model_path: Path, base_model: Path, provider: str, language: str, use_itn: bool,
    ) -> None:
        self.tokens = json.loads((base_model / "tokens.json").read_text(encoding="utf-8"))
        auto_model = AutoModel(
            model=str(base_model),
            device="cuda" if provider != "CPUExecutionProvider" else "cpu",
            disable_update=True,
        )
        self.frontend = auto_model.kwargs["frontend"]
        self.language_id = _LANGUAGE_IDS[language]
        self.textnorm_id = _TEXTNORM_IDS["with_itn" if use_itn else "without_itn"]
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_options.intra_op_num_threads = 1
        session_options.inter_op_num_threads = 1
        provider_options: list[dict[str, Any]] | None = None
        if provider == "TensorrtExecutionProvider":
            provider_options = [
                {
                    "trt_engine_cache_enable": True,
                    "trt_engine_cache_path": str(ROOT / "artifacts" / "group1_voice" / "trt_cache"),
                    "trt_fp16_enable": True,
                }
            ]
        elif provider == "CUDAExecutionProvider":
            provider_options = [{"cudnn_conv_use_max_workspace": "1"}]
        self.session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=[provider],
            provider_options=provider_options,
        )
        self.input_names = {item.name for item in self.session.get_inputs()}
        speech_input = next(item for item in self.session.get_inputs() if item.name == "speech")
        self.fixed_frames = (
            int(speech_input.shape[1])
            if len(speech_input.shape) >= 3 and isinstance(speech_input.shape[1], int)
            else None
        )
        self.provider = provider

    def transcribe(self, audio_path: Path) -> tuple[str, dict[str, float]]:
        started = time.perf_counter()
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

        frontend_started = time.perf_counter()
        wave_tensor = torch.from_numpy(waveform).unsqueeze(0)
        wave_lengths = torch.tensor([wave_tensor.shape[1]], dtype=torch.int32)
        feats, feat_lens = self.frontend(wave_tensor, wave_lengths)
        actual_feat_len = int(feat_lens[0])
        if self.fixed_frames is not None and feats.shape[1] != self.fixed_frames:
            if feats.shape[1] > self.fixed_frames:
                feats = feats[:, : self.fixed_frames, :]
                feat_lens = torch.tensor([self.fixed_frames], dtype=torch.int32)
            else:
                pad_frames = self.fixed_frames - feats.shape[1]
                feats = torch.nn.functional.pad(feats, (0, 0, 0, pad_frames))
        frontend_ms = (time.perf_counter() - frontend_started) * 1000.0

        ort_started = time.perf_counter()
        feeds: dict[str, np.ndarray] = {
            "speech": feats.cpu().numpy().astype("float32"),
        }
        if "speech_lengths" in self.input_names:
            feeds["speech_lengths"] = feat_lens.cpu().numpy().astype("int32")
        if "language" in self.input_names:
            feeds["language"] = np.array([self.language_id], dtype=np.int32)
        if "textnorm" in self.input_names:
            feeds["textnorm"] = np.array([self.textnorm_id], dtype=np.int32)
        logits, output_lens = self.session.run(None, feeds)
        onnx_ms = (time.perf_counter() - ort_started) * 1000.0

        ids = logits[0].argmax(axis=-1).tolist()
        # The fixed-shape graph pads short utterances to ``fixed_frames`` and its
        # output length therefore includes padded tail frames.  SenseVoice adds
        # four control-query frames before the acoustic features; decoding past
        # the real feature length produces deterministic suffix hallucinations.
        limit = min(int(output_lens[0]), actual_feat_len + 4)
        collapsed: list[int] = []
        previous = None
        for token_id in ids[:limit]:
            if token_id != previous and token_id != 0:
                collapsed.append(token_id)
            previous = token_id
        pieces = [self.tokens[token_id] for token_id in collapsed]
        raw_text = "".join(pieces)
        text = _strip_and_correct(rich_transcription_postprocess(raw_text))
        total_ms = (time.perf_counter() - started) * 1000.0
        return text, {
            "frontend_ms": round(frontend_ms, 3),
            "onnx_ms": round(onnx_ms, 3),
            "total_ms": round(total_ms, 3),
        }

    def warmup(self, audio_root: Path, manifest: list[dict[str, Any]], rounds: int) -> None:
        for item in manifest[:rounds]:
            self.transcribe(audio_root / item["audio"])


def _run_item(item: dict[str, Any], audio_root: Path, recognizer: OnnxSenseVoice) -> dict[str, Any]:
    audio_path = audio_root / item["audio"]
    text, latency = recognizer.transcribe(audio_path)

    nlu_started = time.perf_counter()
    b1 = process_asr_text(
        request_id=str(item.get("id") or item["audio"]),
        text=text,
        asr_confidence=1.0,
    )
    b2 = parse_command(b1)
    nlu_ms = round((time.perf_counter() - nlu_started) * 1000.0, 3)

    expected_text = item["text"]
    normalized_reference = _normalize_transcript(expected_text)
    normalized_hypothesis = _normalize_transcript(text)
    edit_distance = _edit_distance(normalized_reference, normalized_hypothesis)

    return {
        "id": str(item.get("id") or item["audio"]),
        "source_id": item.get("source_id"),
        "language": item.get("lang"),
        "audio": item["audio"],
        "reference_text": expected_text,
        "expected_intent": item.get("intent"),
        "expected_slots": item.get("slots", {}),
        "asr_text": text,
        "asr_exact": normalized_hypothesis == normalized_reference,
        "intent_ok": b2.get("intent") == item.get("intent"),
        "slots_ok": _slots_match(
            dict(b2.get("slots", {})),
            dict(item.get("slots", {})),
        ),
        "reference_chars": len(normalized_reference),
        "edit_distance": edit_distance,
        "latency": {
            "frontend_ms": latency["frontend_ms"],
            "onnx_ms": latency["onnx_ms"],
            "nlu_ms": nlu_ms,
            "model_nlu_ms": round(latency["onnx_ms"] + nlu_ms, 3),
            "total_ms": round(latency["total_ms"] + nlu_ms, 3),
        },
        "predicted_intent": b2.get("intent"),
        "predicted_slots": b2.get("slots", {}),
        "status": b2.get("status"),
    }


def _summarize(records: list[dict[str, Any]], latency_samples: int) -> dict[str, Any]:
    total = len(records)
    reference_chars = sum(record["reference_chars"] for record in records)
    edit_errors = sum(record["edit_distance"] for record in records)
    latency_records = records[:latency_samples]
    return {
        "total": total,
        "asr_exact_accuracy": round(sum(record["asr_exact"] for record in records) / total, 6) if total else 0.0,
        "asr_character_accuracy": round(max(0.0, 1.0 - edit_errors / reference_chars), 6) if reference_chars else 0.0,
        "intent_accuracy": round(sum(record["intent_ok"] for record in records) / total, 6) if total else 0.0,
        "slot_accuracy": round(sum(record["slots_ok"] for record in records) / total, 6) if total else 0.0,
        "latency_sample_count": len(latency_records),
        "latency": {
            key: _latency_stats([float(record["latency"][key]) for record in latency_records])
            for key in ("frontend_ms", "onnx_ms", "nlu_ms", "model_nlu_ms", "total_ms")
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    parser.add_argument("--onnx-model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--base-model", type=Path, default=SENSEVOICE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--provider", default="CUDAExecutionProvider")
    parser.add_argument("--language", choices=sorted(_LANGUAGE_IDS), default="zh")
    parser.add_argument("--use-itn", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--latency-samples", type=int, default=50)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.limit is not None:
        manifest = manifest[: args.limit]

    recognizer = OnnxSenseVoice(
        model_path=args.onnx_model,
        base_model=args.base_model,
        provider=args.provider,
        language=args.language,
        use_itn=args.use_itn,
    )
    recognizer.warmup(args.audio_root, manifest, rounds=args.warmup)
    process_asr_text(request_id="warmup-nlu", text="保持当前车道。", asr_confidence=1.0)

    records = [_run_item(item, args.audio_root, recognizer) for item in manifest]
    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest),
        "audio_root": str(args.audio_root),
        "onnx_model": str(args.onnx_model),
        "provider": args.provider,
        "language": args.language,
        "use_itn": args.use_itn,
        "sample_limit": args.limit,
        "warmup": args.warmup,
        "git": _git_state(),
        "overall": _summarize(records, args.latency_samples),
        "records": records,
    }
    _write_json(args.output, report)
    _write_markdown(args.output.with_suffix(".md"), report)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

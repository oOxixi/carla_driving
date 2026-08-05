"""Prepare/check release inputs and render the raw-backed B-role handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


INT4_LATENCY = "qwen3vl_2b_gptq_int4_marlin_vllm_cu132_latency_gate_prompt_v3.json"
INT4_CONTRACT = "qwen3vl_2b_gptq_int4_marlin_vllm_cu132_target10_prompt_v3.json"
HISTORICAL = (
    "qwen25_3b_awq_0803_frozen320_baseline.json",
    "qwen3vl_2b_fp8_vllm_cu132_latency_gate.json",
    INT4_LATENCY,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _stage_release_data(root: Path) -> None:
    package = root / "release_assets/package"
    frozen = package / "datasets/frozen_validation"
    stress = root / "artifacts/four_modal_0728/stress_set"
    sources = {
        "ASR dataset": root / "voice_group/test_samples",
        "multimodal cases": stress / "cases_v2.jsonl",
        "multimodal images": stress / "images",
        "multimodal LiDAR": stress / "lidar",
        "latency manifest": root / "datasets/repro/full_chain_latency_v1.json",
        "scenarios": root / "scenarios",
        "smoke MP3": root / "voice_group/test_samples/dialect/dongbei/0081.mp3",
    }
    missing = [f"{label}: {path}" for label, path in sources.items() if not path.exists()]
    if missing:
        raise FileNotFoundError("release data source missing: " + "; ".join(missing))
    shutil.copytree(sources["ASR dataset"], frozen / "asr", dirs_exist_ok=True)
    multimodal = frozen / "multimodal"
    multimodal.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sources["multimodal cases"], multimodal / "cases.jsonl")
    shutil.copytree(sources["multimodal images"], multimodal / "images", dirs_exist_ok=True)
    shutil.copytree(sources["multimodal LiDAR"], multimodal / "lidar", dirs_exist_ok=True)
    manifest = json.loads(sources["latency manifest"].read_text(encoding="utf-8"))
    for sample in manifest["samples"]:
        sample["audio_ref"] = "asr/" + str(sample["audio_ref"]).split("voice_group/test_samples/", 1)[-1]
        sample["frame_ref"] = "multimodal/images/" + Path(str(sample["frame_ref"])).name
    _write_json(frozen / "full_chain_latency_v1.json", manifest)
    shutil.copytree(sources["scenarios"], package / "scenarios", dirs_exist_ok=True)
    audio = package / "samples/audio/smoke_set_speed_20.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    if not audio.is_file():
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is not None:
            result = subprocess.run(
                [ffmpeg, "-y", "-i", str(sources["smoke MP3"]), "-ac", "1", "-ar", "16000",
                 "-c:a", "pcm_s16le", str(audio)],
                text=True, capture_output=True, check=False,
            )
            if result.returncode:
                raise RuntimeError("ffmpeg smoke WAV conversion failed: " + result.stderr[-1000:])
        else:
            import numpy as np
            import soundfile as sf

            samples, sample_rate = sf.read(
                sources["smoke MP3"], dtype="float32", always_2d=True
            )
            mono = samples.mean(axis=1)
            target_size = round(len(mono) * 16000 / sample_rate)
            positions = np.linspace(0, len(mono), target_size, endpoint=False)
            mono_16k = np.interp(positions, np.arange(len(mono)), mono).astype("float32")
            sf.write(audio, mono_16k, 16000, subtype="PCM_16")
    commands = package / "samples/commands.jsonl"
    commands.write_text(json.dumps({
        "audio": "samples/audio/smoke_set_speed_20.wav",
        "expected_transcript": "速度设为20公里。",
        "intent": "SET_SPEED",
        "speed_kph": 20,
    }, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare_metrics(root: Path) -> None:
    source = root / "artifacts/B_role_validation"
    missing = [name for name in (*HISTORICAL, INT4_CONTRACT) if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError("raw B-role JSON missing: " + ", ".join(missing))
    historical = root / "metrics/historical_5070/raw"
    historical.mkdir(parents=True, exist_ok=True)
    for name in HISTORICAL:
        shutil.copy2(source / name, historical / name)
    (historical.parent / "README.md").write_text(
        "# RTX 5070 historical diagnostics\n\n"
        "These three raw JSON files are preserved diagnostics, not official full-chain results. "
        "They were copied byte-for-byte and were not rerun during packaging.\n",
        encoding="utf-8",
    )

    latency_path = source / INT4_LATENCY
    contract_path = source / INT4_CONTRACT
    latency = json.loads(latency_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    ref = root / "metrics/reference_5070"
    for child in (ref / "metrics", ref / "raw", ref / "logs"):
        child.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latency_path, ref / "raw" / latency_path.name)
    shutil.copy2(contract_path, ref / "raw" / contract_path.name)
    kernel_source = source / "qwen3vl_2b_gptq_int4_marlin_cu132_kernel_evidence.txt"
    if kernel_source.is_file():
        shutil.copy2(kernel_source, ref / "logs" / kernel_source.name)
    else:
        (ref / "logs/NOT_AVAILABLE.md").write_text("Runtime kernel log was not available.\n", encoding="utf-8")

    raw_latency = latency["latency_ms"]
    raw_metrics = contract["metrics"]
    latency_metric = {
        "status": "MEASURED_DIAGNOSTIC",
        "scope": latency["dataset_kind"],
        "warmups": latency["warmups"],
        "count": raw_latency["count"],
        "mean_ms": raw_latency["mean_ms"],
        "p50_ms": raw_latency["p50_ms"],
        "p95_ms": raw_latency["p95_ms"],
        "max_ms": raw_latency["max_ms"],
        "official_end_to_end": {"status": "NOT_RUN", "reason": "no_formal_full_chain_5070_run"},
        "source": f"raw/{latency_path.name}",
    }
    accuracy_metric = {
        "proxy_contract": {
            "status": "MEASURED_DIAGNOSTIC",
            "passed": int(contract["ready"] * raw_metrics["all_contract_accuracy"]),
            "total": contract["total"],
            "accuracy": raw_metrics["all_contract_accuracy"],
            "scope": contract["dataset_kind"],
            "source": f"raw/{contract_path.name}",
        },
        "official_asr": {"status": "NOT_RUN", "reason": "no_formal_full_chain_5070_run"},
        "official_multimodal": {"status": "NOT_RUN", "reason": "proxy_set_is_not_official_full_chain"},
    }
    _write_json(ref / "metrics/latency.json", latency_metric)
    _write_json(ref / "metrics/accuracy.json", accuracy_metric)
    _write_json(ref / "metrics/scenarios.json", {
        "status": "NOT_RUN", "reason": "no_physical_carla_reference_run"
    })
    _write_json(ref / "metrics/stability.json", {
        "status": "NOT_RUN", "reason": "official_end_to_end_p95_not_measured"
    })
    _write_json(ref / "environment.json", {
        "hardware_label": "RTX 5070 reference",
        "gpu": latency["gpu"],
        "cuda_userspace": "13.2",
        "source_created_at_utc": latency["created_at_utc"],
    })
    _write_json(ref / "model_manifest.json", {
        "profile": "qwen3vl-2b-int4",
        "model_id": latency["model"],
        "revision": contract["model_revision"],
        "quantization": "GPTQ INT4",
        "required_linear_kernel": "MarlinLinearKernel",
        "visual_tokens": 64,
    })
    files = {}
    for path in sorted(item for item in ref.rglob("*") if item.is_file()):
        if path.name in {"run_manifest.json", "README.md"}:
            continue
        files[path.relative_to(ref).as_posix()] = sha256_file(path)
    _write_json(ref / "run_manifest.json", {
        "run_id": "rtx5070-int4-diagnostic-20260802",
        "status": "PARTIAL_REFERENCE",
        "claim_scope": "Qwen service diagnostic plus 10-case local proxy contract",
        "formal_full_chain": "NOT_RUN",
        "scenario_completion": "NOT_RUN",
        "a800": "NOT_RUN",
        "files": files,
    })
    (ref / "README.md").write_text(
        "# RTX 5070 reference\n\n"
        "Status: `PARTIAL_REFERENCE`. Raw-backed Qwen-only hot latency: "
        f"P50 `{raw_latency['p50_ms']:.2f} ms`, P95 `{raw_latency['p95_ms']:.2f} ms`, "
        f"max `{raw_latency['max_ms']:.2f} ms`; local proxy contract "
        f"`{int(contract['ready'] * raw_metrics['all_contract_accuracy'])}/{contract['total']}`.\n\n"
        "Formal ASR, formal full-chain end-to-end latency, physical CARLA scenario completion, "
        "30-minute stability, and A800 measurements are `NOT_RUN`; no score claim is made for them.\n",
        encoding="utf-8",
    )
    _stage_release_data(root)


def check_release(root: Path) -> list[str]:
    required = {
        "primary Qwen weights": root / "release_assets/weights/qwen3vl-2b-int4",
        "SenseVoice weights": root / "release_assets/weights/asr/SenseVoiceSmall",
        "Docker archive image.tar": root / "dist/carla-language-control-submission/image.tar",
        "technical solution PDF": root / "submission/技术方案.pdf",
        "CARLA demo video": root / "submission/demo/carla_closed_loop.mp4",
        "RTX 5070 reference manifest": root / "metrics/reference_5070/run_manifest.json",
    }
    missing = []
    for label, path in required.items():
        if path.is_dir():
            if not any(item.is_file() for item in path.rglob("*")):
                missing.append(f"{label} is empty: {path}")
        elif not path.is_file():
            missing.append(f"{label} missing: {path}")
    return missing


def render_handoff(reference: Path, output: Path) -> None:
    latency = json.loads((reference / "metrics/latency.json").read_text(encoding="utf-8"))
    accuracy = json.loads((reference / "metrics/accuracy.json").read_text(encoding="utf-8"))
    scenarios = json.loads((reference / "metrics/scenarios.json").read_text(encoding="utf-8"))
    proxy = accuracy["proxy_contract"]
    text = f"""# B Role Reproduction Handoff (0804)

## Scope

Qwen model selection, CUDA 13.2/vLLM offline deployment, latency-first validation, and reproducible package entry points. No A800 result is inferred from RTX 5070 data.

## Default Route

`h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4` at revision `f91db2369bd00e7ec20bf09b6a0080cdb26aefa5`, GPTQ INT4 + Marlin, 64 visual tokens. FP8 revision is `46485250d8854c0a9be4f1adbc67ca47e5bb6fa5`; optional 3B revision is `66285546d2b821cf421d4f5eb2576359d3770cd3`.

## RTX 5070 Results

Raw-backed Qwen service diagnostic: P50 `{latency['p50_ms']:.2f} ms`, P95 `{latency['p95_ms']:.2f} ms`, max `{latency['max_ms']:.2f} ms`, `{latency['count']}` measured requests after `{latency['warmups']}` warmups. Local proxy action/target contract: `{proxy['passed']}/{proxy['total']}`. These are not formal end-to-end or official accuracy results.

## A800 Status

`NOT_RUN`. All A800 latency, accuracy, scenario, and stability fields remain unmeasured.

## Evidence Index

- `{reference / 'run_manifest.json'}`
- `{reference / 'metrics/latency.json'}`
- `{reference / 'metrics/accuracy.json'}`
- `{reference / 'raw'}`
- `{reference / 'logs'}`

## Reproduction

```bash
docker load -i image.tar
./run.sh preflight --profile a800-safe
./run.sh evaluate --profile a800-safe
./stop.sh
./run.sh preflight --profile a800-optimized
./run.sh evaluate --profile a800-optimized
./run.sh stability --profile a800-optimized
./stop.sh
```

Run stability only after optimized evaluation reaches or approaches the official latency line. Generate A800 evidence on the A800; never copy RTX 5070 values.

## Known Limits

- Formal full-chain end-to-end latency: `NOT_RUN` (`no_formal_full_chain_5070_run`).
- Formal ASR/multimodal accuracy: `NOT_RUN`.
- CARLA physical scenario completion: `{scenarios['status']}` (`{scenarios['reason']}`).
- `image.tar`, weights, PDF, and video are release-time external artifacts and are not fabricated by this source commit.

## Next Operator

Run `python tools/build_submission_package.py check`. Supply only the reported missing artifacts, then run A800 `preflight` and latency-first `evaluate`. Promote the resulting immutable run; run correctness/stability only when the recorded gate allows it.
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--root", type=Path, default=Path("."))
    check = sub.add_parser("check")
    check.add_argument("--root", type=Path, default=Path("."))
    render = sub.add_parser("render-handoff")
    render.add_argument("--reference-run", type=Path, default=Path("metrics/reference_5070"))
    render.add_argument("--output", type=Path, default=Path("HANDOFF_B_REPRO_0804.md"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare_metrics(args.root.resolve())
        return 0
    if args.command == "check":
        missing = check_release(args.root.resolve())
        if missing:
            print("release check failed:\n- " + "\n- ".join(missing))
            return 2
        print("release check passed")
        return 0
    render_handoff(args.reference_run, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

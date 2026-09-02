"""Check release inputs and render the raw-backed Qwen 2B reproduction guide."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


INT4_LATENCY = "qwen3vl_2b_gptq_int4_marlin_vllm_cu132_latency_gate_prompt_v3.json"
INT4_CONTRACT = "qwen3vl_2b_gptq_int4_marlin_vllm_cu132_target10_prompt_v3.json"
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        elif path.stat().st_size == 0:
            missing.append(f"{label} is empty: {path}")
    return missing


def render_handoff(reference: Path, output: Path) -> None:
    latency = json.loads((reference / "metrics/latency.json").read_text(encoding="utf-8"))
    accuracy = json.loads((reference / "metrics/accuracy.json").read_text(encoding="utf-8"))
    scenarios = json.loads((reference / "metrics/scenarios.json").read_text(encoding="utf-8"))
    proxy = accuracy["proxy_contract"]
    text = f"""# Qwen 2B Reproduction Guide

## Scope

Qwen model selection, CUDA 13.2/vLLM offline deployment, latency-first validation, and reproducible package entry points. No A800 result is inferred from RTX 5070 data.

## Default Route

`h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4` at revision `f91db2369bd00e7ec20bf09b6a0080cdb26aefa5`, GPTQ INT4 + Marlin, 64 visual tokens. The only alternate profile is the 2B FP8 revision `46485250d8854c0a9be4f1adbc67ca47e5bb6fa5`.

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
    check = sub.add_parser("check")
    check.add_argument("--root", type=Path, default=Path("."))
    render = sub.add_parser("render-handoff")
    render.add_argument("--reference-run", type=Path, default=Path("metrics/reference_5070"))
    render.add_argument(
        "--output", type=Path, default=Path("docs/reproduction/QWEN2B_REPRODUCTION.md")
    )
    args = parser.parse_args()
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

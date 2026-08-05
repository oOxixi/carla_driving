# Independent Reproduction Guide

## Package Contents

The final release contains `image.tar`, Docker Compose, `run.sh`/`run.ps1`, frozen datasets and scenarios, fixed model revisions/download fallbacks, this guide, the read-only notebook, raw-backed metrics/logs, a technical PDF, and a CARLA closed-loop video. Source checkout validation is available with:

```bash
python tools/build_submission_package.py check
```

The command fails clearly while any release-time artifact is absent; it never fabricates a placeholder.

After fixed-revision weights are supplied, run `python tools/build_submission_package.py prepare --root .` once to refresh raw-backed metrics and staged release inputs, then run `check`.

## Hardware and Software

- Development reference: NVIDIA RTX 5070 Laptop GPU, 8 GB class VRAM.
- Formal target: NVIDIA A800.
- CUDA userspace/toolchain: 13.2; controller/Qwen runtime is installed from locked Linux CPython 3.12 wheelhouses.
- CARLA: 0.9.16; vLLM: repository-built CUDA 13.2 wheel; Docker Engine with Compose and NVIDIA Container Toolkit is the only host runtime dependency.

## Inputs

The controller consumes frozen 16 kHz speech, RGB/LiDAR, vehicle state, weather/road context, and immutable scenario definitions under `/app/release_data`. The default model is Qwen3-VL 2B GPTQ INT4 with Marlin and a fixed 64-token visual budget. Input hashes are recorded by preflight.

## Outputs

Every command writes a unique directory below `/output/runs/` with `run_manifest.json`, `environment.json`, metrics, logs, and raw evidence. `output/latest_run_id.txt` is only a convenience pointer; promotion verifies the selected manifest and hashes.

Available explicit modes are `preflight`, `smoke`, `evaluate`, `demo`, and `stability`. Stability is never implicit.

## RTX 5070 Reference Run

Current committed evidence is deliberately partial: a raw-backed fixed-image hot Qwen diagnostic measured 5 warmups followed by 10 requests at P50 74.03 ms, P95 83.85 ms, and max 84.19 ms; a separate frozen local proxy recorded action/target contract 10/10. These are not formal dynamic-frame end-to-end latency, ASR accuracy, CARLA completion, or stability claims. See `metrics/reference_5070` and `metrics/historical_5070/raw`.

Run a real package on RTX 5070 with:

```bash
docker load -i image.tar
./run.sh preflight --profile rtx5070
./run.sh smoke --profile rtx5070
./run.sh evaluate --profile rtx5070
./stop.sh
```

## A800 Formal Run

Start safely, then test the optimized profile only from a clean stopped stack:

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

Run `stability` only after optimized evaluation reaches or approaches the official latency line. A800 results must be generated on the A800, never copied from RTX 5070 evidence. PowerShell uses the equivalent `./run.ps1 MODE -Profile PROFILE` and `./stop.ps1 -Profile PROFILE` commands.

## Expected Results

The official targets are speech parsing P95 `<= 50 ms`, end-to-end decision P95 `<= 150 ms`, speech recognition accuracy `>= 95%`, multimodal alignment/contract accuracy `>= 98%`, and scenario completion `>= 90%`. In `evaluate`, end-to-end P95 `> 300 ms` is only an early-stop rule: accuracy and CARLA scenarios are skipped to avoid waste; it is not the official pass line. Fixed-image hot latency is diagnostic, while formal latency uses content-unique dynamic frames through the full chain.

## Failure States

- `FAILED`: preflight, command, hash, service, or scenario error; the exact reason is retained.
- `EARLY_STOP`: measured end-to-end P95 exceeded 300 ms; correctness and scenarios were not run.
- `NOT_RUN`: no measurement exists; it never means zero or pass.
- `PARTIAL_REFERENCE`: raw evidence exists for only the stated diagnostic scope.

`tools/build_submission_package.py check` must report missing weights, `image.tar`, PDF, or video instead of allowing an incomplete submission.

## Model and Dataset Revisions

- Default INT4: `h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4`, revision `f91db2369bd00e7ec20bf09b6a0080cdb26aefa5`.
- Optional FP8: `Qwen/Qwen3-VL-2B-Instruct-FP8`, revision `46485250d8854c0a9be4f1adbc67ca47e5bb6fa5`.
- Optional 3B: `Qwen/Qwen2.5-VL-3B-Instruct`, revision `66285546d2b821cf421d4f5eb2576359d3770cd3`.
- A800 7B migration: `Qwen/Qwen2.5-VL-7B-Instruct-AWQ`, revision `536a35794df8831aa814970ee8f89eff577e7718`; see `docs/QWEN25_VL_7B_A800_MIGRATION.md`.
- ASR: `iic/SenseVoiceSmall`, revision `7bf452403abd7353a300cd760f7adae7701c92c1`.
- Frozen validation manifests are under `datasets/frozen_validation`; preflight records their SHA-256 values.

## Troubleshooting

Run `./run.sh preflight --profile PROFILE` first. If Docker, NVIDIA runtime, model/dataset hashes, Qwen Marlin evidence, or CARLA readiness fails, fix that single reported cause and rerun preflight. Do not run accuracy, stability, PDF/video rendering, or another model while the latency/preflight gate is failing. Stop preserves `/output`; it does not remove volumes.

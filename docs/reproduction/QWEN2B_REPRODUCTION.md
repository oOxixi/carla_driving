# Qwen 2B Reproduction Guide

## Scope

Qwen model selection, CUDA 13.2/vLLM offline deployment, latency-first validation, and reproducible package entry points. No A800 result is inferred from RTX 5070 data.

## Default Route

`h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4` at revision `f91db2369bd00e7ec20bf09b6a0080cdb26aefa5`, GPTQ INT4 + Marlin, 64 visual tokens. The only alternate profile is the 2B FP8 revision `46485250d8854c0a9be4f1adbc67ca47e5bb6fa5`.

## RTX 5070 Results

Raw-backed Qwen service diagnostic: P50 `74.03 ms`, P95 `83.85 ms`, max `84.19 ms`, `10` measured requests after `5` warmups. Local proxy action/target contract: `10/10`. These are not formal end-to-end or official accuracy results.

## A800 Status

`NOT_RUN`. All A800 latency, accuracy, scenario, and stability fields remain unmeasured.

## Evidence Index

- `metrics\reference_5070\run_manifest.json`
- `metrics\reference_5070\metrics\latency.json`
- `metrics\reference_5070\metrics\accuracy.json`
- `metrics\reference_5070\raw`
- `metrics\reference_5070\logs`

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
- CARLA physical scenario completion: `NOT_RUN` (`no_physical_carla_reference_run`).
- `image.tar`, weights, PDF, and video are release-time external artifacts and are not fabricated by this source commit.

## Next Operator

Run `python tools/build_submission_package.py check`. Supply only the reported missing artifacts, then run A800 `preflight` and latency-first `evaluate`. Promote the resulting immutable run; run correctness/stability only when the recorded gate allows it.

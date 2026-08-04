# CARLA-Language-Benchmark v1

## Frozen Release

This repository contains the frozen, model-neutral CARLA language instruction
benchmark. It has 6192 records and zero language/schema audit errors.

## Repository Layout

```
CARLA-Language-Benchmark/
├── datasets/final_benchmark/
│   └── CARLA_language_benchmark_v1_normalized.json
├── baseline/freeze_p0/
│   ├── dataset_checksum.json
│   └── metric_policy.json
├── tools/
│   └── audit_global_benchmark_v1.py
├── dataset_card.json
├── HANDOFF.md
└── README.md
```

## Evaluation Boundary

This release freezes only model-neutral language/schema regression inputs. It
contains no frozen multimodal validation split and no formal accuracy result.
`baseline/freeze_p0/metric_policy.json` names the future validation artifact
contract; formal accuracy reporting remains prohibited until that asset exists.

## Usage

```bash
python tools/audit_global_benchmark_v1.py \
  datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json \
  --checksum baseline/freeze_p0/dataset_checksum.json
```

# CARLA-Language-Benchmark v1

## Frozen Release

This repository contains the frozen CARLA language instruction benchmark.

Statistics:
- Total records: 6192
- Global audit errors: 0

## Repository Layout

```
CARLA-Language-Benchmark/
├── datasets/
│   └── final_benchmark/
│       └── CARLA_language_benchmark_v1_normalized.json
├── baseline/
│   └── freeze_p0/
│       ├── baseline_manifest.json
│       ├── checksum.json
│       ├── freeze_report.json
│       ├── latency_schema.json
│       ├── metric_policy.json
│       └── validation_protocol.json
├── tools/
│   ├── audit_global_benchmark_v1.py
│   ├── merge_carla_language_benchmark_v1.py
│   └── normalize_carla_benchmark_schema_v1.py
├── README.md
├── HANDOFF.md
└── dataset_card.json
```

## Usage

```python
import json

with open(
    "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json",
    encoding="utf-8"
) as f:
    data = json.load(f)

print(data[0]["template"])
print(data[0]["expected_action"])
```

## Baseline Protocol

The release includes:
- frozen scoring protocol
- 320-sample four-modality baseline package reference
- stage-wise latency profiling protocol

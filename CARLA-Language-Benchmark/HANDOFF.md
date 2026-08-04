# CARLA-Language-Benchmark v1 Handoff

## Scope

The language benchmark is frozen at 6192 records for language/schema
regression. This package does not provide a frozen multimodal validation split
or a formal accuracy result. The required future validation artifact is
declared in `baseline/freeze_p0/metric_policy.json`.

## Record Interface

Every record contains:

- `id`
- `category`
- `template`
- `variables`
- `semantic_intent`
- `scene_generator`
- `scene_constraints`
- `expected_action`
- `expected_parameters`
- `safety_policy`

## Validation

Run:

```bash
python tools/audit_global_benchmark_v1.py \
  datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json \
  --checksum baseline/freeze_p0/dataset_checksum.json
```

Expected: 6192 records and zero errors.

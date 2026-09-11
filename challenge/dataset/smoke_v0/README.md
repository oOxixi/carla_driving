# B1 Teacher Smoke Dataset v0

Dataset version: `teacher_distill_v0.1_smoke`

## 1. Purpose

This is the B1 Teacher-data Smoke Test delivery package.

Validated pipeline:

ModelRequest V1 → actual Teacher RGB → Qwen/Qwen3.5-2B → ManeuverPlan V2 → closed-loop quality → target pointer → training policy → group-aware Train/Val split

## 2. Final Counts

- Raw structurally valid Teacher samples: 30
- Train-eligible samples: 28
- Quarantined hard cases: 2
- Train samples: 22
- Val samples: 6
- Safety override samples retained: 7
- Run-status inconsistent but command successful: 2

## 3. Teacher

- Model: `Qwen/Qwen3.5-2B`
- Git SHA: `a05c8b76efcd4c176965223c661f40b153cb1836`
- Planner mode: `planner_v2`

## 4. Target Pointer Smoke Configuration

- TopK = 8
- Valid pointers = 0..7
- NO_TARGET = 8
- Candidate order preserves ModelRequest.targets order
- TARGET_OUTSIDE_TOPK must never silently become NO_TARGET

Current Student V0 / A3 contract freezes max_targets=8 and NO_TARGET=8; the canonical B1 dataset still preserves the complete ModelRequest.targets.

## 5. Training Policy

Raw Teacher supervision is retained separately from normal supervised training eligibility.

Train eligible requires:

- teacher_label_valid = true
- closed_loop_success = true

Two hard cases are quarantined:

- ACC_A05_lane_change_left
- SUP_A13_lane_change_right

Both terminate with `LANE_GAP_UNSAFE`.

SafetySupervisor intervention does not automatically invalidate an otherwise successful sample.

## 6. Train / Val Split

- Split seed = 1
- Train = 22 samples
- Val = 6 samples
- Train groups = 10
- Val groups = 2
- Group overlap = 0
- Sample ID overlap = 0

Group definition:

`scenario_family + map + route_hash + seed`

Frame-level random splitting is forbidden.

## 7. Directory Layout

```text
smoke_v0/
├── README.md
├── dataset_schema.md
├── data/
│   ├── smoke_valid.jsonl
│   ├── smoke_with_targets.jsonl
│   ├── smoke_with_policy.jsonl
│   ├── smoke_train_eligible.jsonl
│   ├── smoke_hard_cases.jsonl
│   ├── smoke_rejected.jsonl
│   ├── train.jsonl
│   └── val.jsonl
├── manifests/
│   ├── dataset_manifest_v0.json
│   ├── train_manifest.json
│   ├── val_manifest.json
│   ├── split_manifest.json
│   ├── rgb_manifest.json
│   └── delivery_manifest.json
├── reports/
│   └── dataset_quality_report.md
└── rgb/
    └── <SHA256>.jpg
```

## 8. Important

This Smoke dataset validates the B1 data pipeline.

It is not the final D3 Train/Val/Test dataset.

<!-- B1_A3_INTERFACE_PATCH_START -->
## Student V0 / A3 Training View

本交付从 `smoke_v0.1.1-interface` 起增加正式下游训练视图：

```text
training_view/
├── train_a3.jsonl
├── val_a3.jsonl
├── a3_view_manifest.json
└── preflight_report.json
```

`data/` 中的数据仍是 B1 canonical/governance 数据。

`training_view/` 是通过 `build_dataset.py` 从 canonical 数据派生的 Student V0 / A3 消费视图。

当前正式 Student V0 contract：

```text
max_steps = 4
max_targets = 8
NO_TARGET = 8
```

Canonical B1 数据仍保留完整 `ModelRequest.targets`。不得把 Student 无法表达的 `TARGET_OUTSIDE_TOPK` 静默映射为 `NO_TARGET`。

本交付已经通过 A3 正式 preflight：

```text
Train 22/22 valid
Val    6/6 valid
Errors 0
Warnings 0
PASS
```
<!-- B1_A3_INTERFACE_PATCH_END -->

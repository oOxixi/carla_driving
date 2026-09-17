# B1 D2 Dataset Delivery

Frozen D2 downstream dataset for Student development.

## Split

- train: 2520 samples
- val: 540 samples
- reserved_test_candidates: 540 samples
- total governed: 3600 samples
- positive eligible: 3395
- hard-negative eligible: 205

Splits are group-aware. Do not move reserved test candidate samples
into training or validation.

## Contents

Each JSONL sample contains:

- ModelRequest V1
- Teacher ManeuverPlan V2
- Teacher/runtime metadata
- closed-loop quality information
- training eligibility/role
- portable RGB reference

RGB assets are stored under:

    challenge/dataset/releases/d2_v1/images/

## Usage

A3:
- train.jsonl for Student training
- val.jsonl for development/model selection

Do NOT use:
- reserved_test_candidates.jsonl for training or tuning

D3 Dataset v1 will supersede this provisional D2 delivery for final
Train/Val/Test/Calibration/official-like freezes.

## Teacher

Teacher profile:

    b1-pinned-teacher-v4

Teacher Git SHA:

    95e97b00def8ec36f12937da34ce8bb9082c4a04

Teacher tag:

    teacher-baseline-v4

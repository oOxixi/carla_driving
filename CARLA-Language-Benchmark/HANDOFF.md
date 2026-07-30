# CARLA-Language-Benchmark v1 Handoff

## Completed Requirements

P0-1:
- scoring protocol frozen
- validation protocol frozen
- latency stages frozen
- baseline protocol frozen

P0-2:
Language benchmark expanded to 6192 records.

Covered categories:
- ordinary instruction
- synonym rewriting
- negation
- compound instruction
- ambiguous target
- missing target
- safety conflict
- unit conversion
- dense target
- occlusion
- detector error
- exposure
- navigation error
- weather failure

## Interface

Every record contains:

id
category
template
variables
semantic_intent
scene_generator
scene_constraints
expected_action
expected_parameters
safety_policy

## Validation

Run:

python tools/audit_global_benchmark_v1.py datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json

Expected:

records=6192
errors=0

## Consumer Workflow

1. Clone repository
2. Load benchmark JSON
3. Read template
4. Use scene_generator for CARLA scene generation
5. Use expected_action for evaluation

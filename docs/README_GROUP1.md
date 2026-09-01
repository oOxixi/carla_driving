# Group1 Voice Qwen RGB Semantic Layer

## Overview

Pipeline:

Voice/Text -\> NLU -\> DrivingCommand -\> Qwen Planner -\> ManeuverPlan
-\> Control/Safety Group

## Important Directories

### datasets

`CARLA-Language-Benchmark/datasets/final_benchmark/extensions/official_language_v1/`

Official instruction extension.

### interfaces

Frozen contracts:

-   driving_command.schema.json
-   model_request.schema.json
-   decision_plan.schema.json
-   maneuver_plan.schema.json
-   perception_state.schema.json
-   control_command.schema.json

### integration

`canonical_bridge.py`

Converts external input into canonical structures.

### runtime

-   orchestrator.py
    -   fast path
    -   Qwen slow path
    -   timeout handling
-   plan_validator.py
    -   validate Qwen plans
-   plan_compiler.py
    -   compile maneuver plans
-   complexity_router.py
    -   route commands

## Testing

Full:

    python -m pytest -q

Current:

    637 passed, 1 skipped

Semantic tests:

    python -m pytest -q integration/tests/test_voice_fast_semantic_coverage.py integration/tests/test_voice_compound_routing.py

## GitHub Checklist

Upload:

-   CARLA-Language-Benchmark
-   interfaces
-   integration
-   runtime
-   voice_group
-   tests
-   docs

Ignore:

-   **pycache**
-   \*.pyc
-   temporary profiling outputs

Before push:

    git status
    git diff --check
    git ls-files

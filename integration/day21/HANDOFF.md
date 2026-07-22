# Day21 Handoff

## Status

Day21 first group task completed.

Completed:

-   Multimodal Qwen decision
-   LiDAR/Safety State input interface
-   Safety priority policy
-   Conflict handling
-   Vehicle command conversion
-   Validation suite

## Module Description

### multimodal_qwen_adapter.py

Receives:

-   voice command
-   scene state
-   perception
-   safety state

Returns:

high-level driving decision.

### safety_schema.py

Provides the interface for second group safety information.

### safety_override.py

Ensures:

Safety \> User command

Examples:

User: 继续走

Safety: RED light

Result: STOP

User: 加速

Safety: pedestrian risk

Result: STOP

### command_adapter.py

Converts decisions to vehicle-side commands.

## Validation

Run:

``` bash
python -m integration.day21.test_day21_multimodal
```

Result:

    DAY21 MULTIMODAL TEST PASS

Run:

``` bash
python -m integration.day21.generate_validation_report
```

Result:

    10/10 cases passed
    accuracy=1.0

## GitHub Usage

After cloning:

``` bash
git clone https://github.com/oOxixi/carla_driving.git
cd carla_driving
```

Run:

``` bash
python -m integration.day21.test_day21_multimodal
```

Generate results:

``` bash
python -m integration.day21.generate_day21_results
```

Do not commit:

-   model weights
-   cache files
-   **pycache**
-   temporary logs

Commit:

    integration/day21/

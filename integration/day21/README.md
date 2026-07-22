# Day21 Multimodal Qwen Safety Decision Module

## Overview

Day21 implements a multimodal autonomous driving high-level decision
module.

Inputs: - Driver voice command - Scene state - Perception summary -
LiDAR / Safety State summary

Output: - START - STOP - SET_SPEED - EMERGENCY_STOP

The module only outputs high-level commands. It does not output
throttle, brake, steer, or actuator control.

------------------------------------------------------------------------

## Architecture

Voice + SceneState + Perception + SafetyState

        |
        v

Day21Context

        |
        v

MultimodalQwenAdapter

        |
        v

Safety Override

        |
        v

Command Adapter

        |
        v

Vehicle-side high-level command

------------------------------------------------------------------------

## Main Interfaces

### Day21Context

``` python
Day21Context(
    voice_command,
    scene_state,
    perception,
    safety_state
)
```

### SafetyStateSummary

Defined in:

    integration/day21/safety_schema.py

Example:

``` python
SafetyStateSummary(
    traffic_light="RED",
    pedestrian_risk=False,
    obstacle_risk=False,
    ttc_s=2.0,
    weather="clear",
    input_confidence=1.0
)
```

Supported fields:

-   traffic_light
-   lidar_object_count
-   nearest_object_distance_m
-   pedestrian_risk
-   obstacle_risk
-   ttc_s
-   weather
-   input_confidence

------------------------------------------------------------------------

## Safety Priority

Safety always overrides user commands.

Priority:

    EMERGENCY_STOP
    >
    STOP
    >
    SET_SPEED
    >
    START

Example:

Voice:

    继续走

Safety:

``` json
{"traffic_light":"RED"}
```

Output:

``` json
{
"intent":"STOP",
"parameters":{}
}
```

------------------------------------------------------------------------

## Run

Test:

``` bash
python -m integration.day21.test_day21_multimodal
```

Generate 10 multimodal cases:

``` bash
python -m integration.day21.generate_day21_results
```

Generate validation:

``` bash
python -m integration.day21.generate_validation_report
```

Expected:

    10/10 cases passed
    accuracy=1.0

------------------------------------------------------------------------

## Test Cases

Included:

1.  Red light stop
2.  Pedestrian stop
3.  Front vehicle slow down
4.  Safe driving continue
5.  Low confidence safety hold
6.  TTC emergency stop
7.  User command conflict
8.  Rain speed reduction
9.  Obstacle stop
10. Normal driving

------------------------------------------------------------------------

## Group2 Interface

Output command example:

STOP:

``` json
{
"intent":"STOP",
"parameters":{}
}
```

SET_SPEED:

``` json
{
"intent":"SET_SPEED",
"parameters":{
"speed":5,
"unit":"m/s"
}
}
```

Group2 can directly map these commands to vehicle-side execution.

------------------------------------------------------------------------

## Error Cases Covered

-   Invalid JSON
-   Markdown output
-   Unsafe START
-   Low confidence execution
-   User command conflict
-   Missing perception

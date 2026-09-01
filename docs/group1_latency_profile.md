# Group1 Challenge Track Profiling Record

## Purpose

Record lightweight deployment related statistics required for
challenge-track preparation.

## Current profiling items

-   command conversion latency
-   schema validation latency
-   Qwen request construction latency
-   slow path timeout
-   plan validation legality

## Recommended future collection

For each frame/request record:

    timestamp
    input token count
    image resolution
    Qwen inference latency
    validation latency
    illegal output count
    memory usage

## Interface principle

Qwen remains a high-level planner.

It does not output:

-   throttle
-   brake
-   steering

All outputs must pass:

    PlanValidator
    State Machine
    Safety Supervisor

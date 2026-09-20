# Vehicle runtime and control modules

本页为可选分组索引。正常开发按 [项目入口](../README.md) 直接进入具体业务模块，再进入功能文档，共三级。

The live entry point is `python -m integration.carla_runner`. This module covers integration, runtime, car_control_A/B/C/D, perception and interfaces. Function pages enumerate implementation files and public entry points.

## Function index

- [Runtime entry and lifecycle](../modules/vehicle-entry.md)
- [Model planning and async contracts](../modules/vehicle-planner.md)
- [Command adaptation and behavior state machines](../modules/vehicle-behavior.md)
- [Route geometry and lateral control](../modules/vehicle-lateral.md)
- [Longitudinal control and conservative sensing](../modules/vehicle-longitudinal.md)
- [Sensor acquisition, detection and source audit](../modules/vehicle-perception.md)
- [Final safety, feedback and scoring](../modules/vehicle-safety.md)
- [Scenario construction, acceptance and evidence](../modules/vehicle-scenarios.md)
- [JSON contracts and process-local objects](../modules/vehicle-interfaces.md)

## Shared boundaries

- JSON schemas are authoritative for inter-module payloads; local dataclasses require adapters.
- CARLA control coordinates use y-right; canonical perception uses y-left. Simulation time is seconds; canonical deadlines are monotonic nanoseconds.
- Strategy defaults mostly come from config/strategy.py; CLI, OrchestratorConfig and model profiles retain separate defaults.
- The live path is runner -> ControlRuntime -> SafetySupervisor. DControlRuntime is a separate canonical wrapper, not the active runner path.
- perception, C delivery helpers and live CARLA acquisition are distinct implementations with similar names.

## Confirmed discrepancies and limitations

1. integration/README.md:102-103 states RGB detection is absent and control still uses truth; optional ONNX detection and control-source auditing now exist.
2. car_control_C/tests/test_safety_state.py:80 and :99 define the same test name twice. The second identical body replaces the first during Python import.
3. carla_runner.py:5953-5959 overrides final_control after D arbitration during startup grace, toward full braking. Document this exception to the single final-output claim.
4. canonical_bridge.py:139-160 substitutes 50 m for missing object range, estimates lateral position from image center times 7 m and assigns zero speed to non-first objects. This is approximate grounding.

This is a static source audit. Test references do not establish live CARLA or hardware acceptance.

# ScenarioRunner evaluator adapter

`integration/scenario_runner_agent.py` implements the CARLA ScenarioRunner
0.9.16 `AutonomousAgent` boundary. It is selected automatically by
`scripts/run_scenario_runner.ps1`.

The adapter does not branch on a repository scenario ID. ScenarioRunner owns
the world, actors, trigger conditions and scenario result; the adapter consumes
the provided sensor frame and global route, then returns one `VehicleControl`.
The requested sensors are front RGB, LiDAR and GNSS—the physical sensor types
supported by the pinned ScenarioRunner AgentWrapper. Speed and heading are
estimated from consecutive GNSS frames.

The frame path is:

```text
ScenarioRunner sensor dictionary
  -> strict shape/finite validation and GNSS motion estimate
  -> unseen global-route steering
  -> speed controller
  -> LiDAR front-corridor distance/TTC
  -> repository D SafetySupervisor
  -> CARLA VehicleControl
```

Prepare the pinned official dependency and run an arbitrary built-in scenario:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fetch_scenario_runner.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_scenario_runner.ps1 `
  -Scenario FollowLeadingVehicle_1
```

An optional `command_file` can be added to the agent JSON config. The file may
contain the frozen voice envelope (`intent`) or high-level decision (`action`).
Invalid, low-confidence, confirmation-required, missing or unsupported command
content fails closed with full braking. Low-level throttle/brake/steer fields
are never accepted as a language command.

This adapter is compatible with evaluator-selected scenario names; it does not
claim to reproduce the organizer's private scoring implementation.

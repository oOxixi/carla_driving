param(
    [Parameter(Mandatory = $true)][string]$Scenario,
    [string]$HostName = "127.0.0.1",
    [int]$Port = 2000,
    [double]$TimeoutSeconds = 60,
    [string]$ScenarioRoot = (Join-Path $PSScriptRoot "..\external\scenario_runner")
)

$ErrorActionPreference = "Stop"
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$ScenarioRoot = [System.IO.Path]::GetFullPath($ScenarioRoot)
$env:PYTHONPATH = "$Root\CARLA_0.9.16\PythonAPI;$ScenarioRoot;$Root"

conda run --no-capture-output -n carla python -c @"
from pathlib import Path
from integration.official_scenario_runner import ScenarioRunnerInvocation, run
run(ScenarioRunnerInvocation(
    root=Path(r'$ScenarioRoot'),
    scenario=r'$Scenario',
    host=r'$HostName',
    port=$Port,
    timeout_s=$TimeoutSeconds,
))
"@

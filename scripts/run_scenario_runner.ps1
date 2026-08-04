param(
    [Parameter(Mandatory = $true)][string]$Scenario,
    [string]$HostName = "127.0.0.1",
    [int]$Port = 2000,
    [double]$TimeoutSeconds = 60,
    [string]$ScenarioRoot = (Join-Path $PSScriptRoot "..\external\scenario_runner"),
    [string]$AgentConfig
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ScenarioRoot = [System.IO.Path]::GetFullPath($ScenarioRoot)
$agentPath = Join-Path $repoRoot 'integration/scenario_runner_agent.py'
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$env:PYTHONPATH = "$repoRoot\CARLA_0.9.16\PythonAPI;$ScenarioRoot;$repoRoot"

$agentConfigForPython = $null
if ($PSBoundParameters.ContainsKey('AgentConfig')) {
    if (-not $AgentConfig.Trim()) {
        throw 'AgentConfig must be a non-empty path when supplied.'
    }
    if (-not (Test-Path -LiteralPath $AgentConfig -PathType Leaf)) {
        throw "AgentConfig does not exist: $AgentConfig"
    }
    $agentConfigForPython = [System.IO.Path]::GetFullPath($AgentConfig)
}

$env:SCENARIO_RUNNER_ROOT = $ScenarioRoot
$env:SCENARIO_RUNNER_SCENARIO = $Scenario
$env:SCENARIO_RUNNER_HOST = $HostName
$env:SCENARIO_RUNNER_PORT = $Port.ToString()
$env:SCENARIO_RUNNER_TIMEOUT = $TimeoutSeconds.ToString([Globalization.CultureInfo]::InvariantCulture)
$env:SCENARIO_RUNNER_AGENT = $agentPath
$env:SCENARIO_RUNNER_AGENT_CONFIG = if ($null -eq $agentConfigForPython) { '' } else { $agentConfigForPython }

& $pythonExe -c @"
import os
from pathlib import Path
from integration.official_scenario_runner import ScenarioRunnerInvocation, run

config = os.environ['SCENARIO_RUNNER_AGENT_CONFIG']
run(ScenarioRunnerInvocation(
    root=Path(os.environ['SCENARIO_RUNNER_ROOT']),
    scenario=os.environ['SCENARIO_RUNNER_SCENARIO'],
    host=os.environ['SCENARIO_RUNNER_HOST'],
    port=int(os.environ['SCENARIO_RUNNER_PORT']),
    timeout_s=float(os.environ['SCENARIO_RUNNER_TIMEOUT']),
    agent_path=Path(os.environ['SCENARIO_RUNNER_AGENT']),
    agent_config=Path(config) if config else None,
))
"@

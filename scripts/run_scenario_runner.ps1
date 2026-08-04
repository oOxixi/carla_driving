param(
    [Parameter(Mandatory = $true)][string]$Scenario,
    [string]$HostName = "127.0.0.1",
    [int]$Port = 2000,
    [double]$TimeoutSeconds = 60,
    [string]$ScenarioRoot = (Join-Path $PSScriptRoot "..\external\scenario_runner"),
    [string]$AgentConfig = (Join-Path $PSScriptRoot "..\examples\scenario_runner_agent_config.json")
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ScenarioRoot = [System.IO.Path]::GetFullPath($ScenarioRoot)
$AgentConfig = [System.IO.Path]::GetFullPath($AgentConfig)
$agentPath = Join-Path $repoRoot 'integration/scenario_runner_agent.py'
$scenarioRunnerScript = Join-Path $ScenarioRoot 'scenario_runner.py'
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$env:PYTHONPATH = "$repoRoot\CARLA_0.9.16\PythonAPI;$ScenarioRoot;$repoRoot"

$scenarioArgs = @(
    '--host', $HostName,
    '--port', $Port,
    '--timeout', $TimeoutSeconds,
    '--scenario', $Scenario,
    '--sync',
    '--output',
    '--json'
)
& $pythonExe $scenarioRunnerScript --agent $agentPath --agentConfig $AgentConfig @scenarioArgs

<#
B3 CARLA measurement entry point (repeatable, no hand-typed commands).

It does four things: pin the interpreter and PYTHONPATH (working around defects
F1/F4 of the repository scripts), confirm the CARLA server is reachable, run the
given scenarios in order, and write every command and result into one manifest
directory.

This file is deliberately ASCII-only: Windows PowerShell 5.1 reads a BOM-less
.ps1 as ANSI, so non-ASCII comments would corrupt the parser.

Usage (dry run first):
  powershell -File challenge/hil/carla_measurement.ps1 -Scenario S01_set_speed_20 -DryRun
  powershell -File challenge/hil/carla_measurement.ps1 -Scenario a,b

Prerequisite: a running CARLA server, e.g.
  D:\CARLA_Latest\CarlaUE4.exe -quality-level=Low
If the server is unreachable the script fails loudly instead of silently
producing an empty run.
#>
param(
    [Parameter(Mandatory = $true)][string[]]$Scenario,
    [ValidateSet("repo", "official")][string]$Runner = "repo",
    [string]$RepoRoot = "",
    [string]$CarlaRoot = "D:\CARLA_Latest",
    [string]$PythonExe = "",
    [string]$ScenarioRoot = "",
    [string]$HostName = "127.0.0.1",
    [int]$Port = 2000,
    [double]$TimeoutSeconds = 180,
    [string]$AgentConfig = "",
    [string]$ExtraArgs = "",
    [switch]$Realtime,
    [string]$OutputRoot = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# `powershell -File script.ps1 -Scenario a,b` hands the whole "a,b" over as one
# string (no comma parsing), so split it here; spaces and repeats are fine.
$Scenario = @(
    $Scenario | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
)
if ($Scenario.Count -eq 0) { throw "-Scenario must name at least one scenario" }

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
} else {
    $RepoRoot = (Resolve-Path $RepoRoot).Path
}
if (-not $ScenarioRoot) {
    $ScenarioRoot = Join-Path $RepoRoot "external\scenario_runner"
}
$ScenarioRoot = [System.IO.Path]::GetFullPath($ScenarioRoot)

if (-not $PythonExe) {
    # Pin the interpreter: the repo script uses whatever "python" is on PATH,
    # and a wrong environment shows up later as mysterious contract failures (F4).
    $PythonExe = "py"
    $PythonArgs = @("-3.12")
} else {
    $PythonArgs = @()
}
if (-not $OutputRoot) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputRoot = Join-Path $RepoRoot ("artifacts\b3\carla_runs\" + $stamp)
}

$entry = Join-Path $PSScriptRoot "carla_measurement_entry.py"
if (-not (Test-Path -LiteralPath $entry -PathType Leaf)) { throw "missing $entry" }
if (-not (Test-Path -LiteralPath $ScenarioRoot -PathType Container)) {
    throw "scenario runner checkout not found: $ScenarioRoot"
}

# F1: PYTHONPATH must contain the scenario_runner checkout itself (it holds
# "agents"), not its parent directory.
$pythonPathEntries = @(
    (Join-Path $CarlaRoot "PythonAPI")
    $ScenarioRoot
    $RepoRoot
)
$env:PYTHONPATH = ($pythonPathEntries -join ";")
$env:CARLA_ROOT = $CarlaRoot

function Test-CarlaServer {
    param([string]$Target, [int]$TargetPort, [int]$TimeoutMs = 2000)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($Target, $TargetPort, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs)) { return $false }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

$serverUp = Test-CarlaServer -Target $HostName -TargetPort $Port
if (-not $serverUp -and -not $DryRun) {
    throw ("CARLA server is not reachable at {0}:{1}. Start it first, e.g. {2}\CarlaUE4.exe " +
           "-quality-level=Low, then re-run (use -DryRun to inspect the plan only).") -f `
        $HostName, $Port, $CarlaRoot
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$plan = [ordered]@{
    schema_version    = "1.0"
    generated_at_utc  = (Get-Date).ToUniversalTime().ToString("o")
    dry_run           = [bool]$DryRun
    repo_root         = $RepoRoot
    runner            = $Runner
    python            = (@($PythonExe) + $PythonArgs) -join " "
    carla_root        = $CarlaRoot
    scenario_root     = $ScenarioRoot
    server            = ("{0}:{1}" -f $HostName, $Port)
    server_reachable  = $serverUp
    pythonpath        = $pythonPathEntries
    output_root       = $OutputRoot
    scenarios         = @()
}

$failed = $false
foreach ($name in $Scenario) {
    $runDir = Join-Path $OutputRoot $name
    $summaryPath = Join-Path $runDir "carla_run_summary.json"
    $logDir = Join-Path $runDir "logs"
    $arguments = @(
        $entry
        "--repo", $RepoRoot
        "--scenario", $name
        "--runner", $Runner
        "--scenario-root", $ScenarioRoot
        "--host", $HostName
        "--port", "$Port"
        "--timeout-s", "$TimeoutSeconds"
        "--log-dir", $logDir
        "--summary-out", $summaryPath
    )
    if ($AgentConfig) { $arguments += @("--agent-config", $AgentConfig) }
    if ($Realtime) { $arguments += "--realtime" }
    # --extra is a REMAINDER argument, so it has to come last.
    if ($ExtraArgs) { $arguments += @("--extra") + ($ExtraArgs -split "\s+") }
    $record = [ordered]@{
        scenario   = $name
        command    = (@($PythonExe) + $PythonArgs + $arguments) -join " "
        output_dir = $runDir
        status     = if ($DryRun) { "DRY_RUN" } else { "PENDING" }
        returncode = $null
    }
    if ($DryRun) {
        Write-Host ("[dry-run] " + $record.command)
    } else {
        New-Item -ItemType Directory -Force -Path $runDir | Out-Null
        Push-Location $RepoRoot
        try {
            & $PythonExe @PythonArgs @arguments
            $record.returncode = $LASTEXITCODE
            if ($LASTEXITCODE -eq 0) {
                $record.status = "SUCCEEDED"
            } else {
                $record.status = "FAILED"
                $failed = $true
            }
        } finally {
            Pop-Location
        }
    }
    $plan.scenarios += $record
}

$planPath = Join-Path $OutputRoot "carla_measurement_plan.json"
$plan | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $planPath -Encoding utf8
Write-Host ("plan -> " + $planPath)
if ($failed) { exit 1 }
exit 0

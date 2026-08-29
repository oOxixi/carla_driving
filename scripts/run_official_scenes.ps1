[CmdletBinding()]
param(
    [ValidateSet('S1', 'S2', 'S3', 'ALL')]
    [string]$Scene = 'ALL',
    [switch]$ValidateOnly,
    [switch]$Smoke,
    [string]$HostAddress = '127.0.0.1',
    [int]$Port = 2000,
    [string]$PythonExecutable = 'py'
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$scenePaths = [ordered]@{
    S1 = 'scenarios/official_competition/S1_basic_voice_control_5km.json'
    S2 = 'scenarios/official_competition/S2_complex_avoidance_8km.json'
    S3 = 'scenarios/official_competition/S3_extreme_emergency_6km.json'
}
$selected = if ($Scene -eq 'ALL') { @('S1', 'S2', 'S3') } else { @($Scene) }
$pythonPrefix = if ($PythonExecutable -eq 'py') { @('-3.12') } else { @() }

Push-Location -LiteralPath $projectRoot
try {
    if ($ValidateOnly) {
        & $PythonExecutable @pythonPrefix 'tools/validate_official_scenes.py'
        if ($LASTEXITCODE -ne 0) { throw 'Official scene static validation failed.' }
        foreach ($id in $selected) {
            & $PythonExecutable @pythonPrefix -m integration.carla_runner `
                --scenario-file $scenePaths[$id] --validate-scenario-only
            if ($LASTEXITCODE -ne 0) { throw "Scenario contract validation failed: $id" }
        }
        return
    }

    foreach ($id in $selected) {
        $arguments = @(
            '-m', 'integration.carla_runner',
            '--host', $HostAddress,
            '--port', $Port,
            '--timeout-s', '60',
            '--warmup-frames', '40',
            '--sensor-warmup-frames', '30',
            '--sensor-timeout-s', '1.0',
            '--perception-mode', 'sensors',
            '--scenario-facts-mode', 'perception',
            '--follow-spectator',
            '--realtime',
            '--print-every', '20',
            '--log-dir', 'artifacts/logs/official_competition',
            '--scenario-file', $scenePaths[$id]
        )
        if ($Smoke) {
            $arguments += @('--max-frames', '600')
        }
        Write-Host "Starting $id using $($scenePaths[$id])"
        & $PythonExecutable @pythonPrefix @arguments
        if ($LASTEXITCODE -ne 0) { throw "Scenario run failed: $id" }
    }
}
finally {
    Pop-Location
}


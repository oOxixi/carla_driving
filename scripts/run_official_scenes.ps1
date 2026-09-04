[CmdletBinding()]
param(
    [ValidateSet('S1', 'S2', 'S3', 'ALL')]
    [string]$Scene = 'ALL',
    [switch]$ValidateOnly,
    [switch]$Smoke,
    [string]$HostAddress = '127.0.0.1',
    [int]$Port = 2000,
    [string]$PythonExecutable = '',
    [string]$QwenServiceUrl = $env:QWEN_SERVICE_URL,
    [ValidateSet('planner_v2')]
    [string]$QwenMode = 'planner_v2',
    [ValidateRange(1.0, 120.0)]
    [double]$QwenTimeoutMs = 100.0,
    [switch]$AllowNonProductionQwen
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$scenePaths = [ordered]@{
    S1 = 'scenarios/official_competition/S1_basic_voice_control_5km.json'
    S2 = 'scenarios/official_competition/S2_complex_avoidance_8km.json'
    S3 = 'scenarios/official_competition/S3_extreme_emergency_6km.json'
}
$selected = if ($Scene -eq 'ALL') { @('S1', 'S2', 'S3') } else { @($Scene) }
if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    if (Get-Command 'py' -ErrorAction SilentlyContinue) {
        $PythonExecutable = (& py -3.12 -c 'import sys; print(sys.executable)').Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($PythonExecutable)) {
            throw 'Python launcher could not resolve a Python 3.12 interpreter.'
        }
    }
    elseif (Get-Command 'python' -ErrorAction SilentlyContinue) {
        $PythonExecutable = 'python'
    }
    else {
        throw 'Python 3.12 was not found; pass -PythonExecutable with an explicit interpreter path.'
    }
}
$pythonPrefix = @()

if (-not $ValidateOnly) {
    if ([string]::IsNullOrWhiteSpace($QwenServiceUrl)) {
        throw 'Official scenes require -QwenServiceUrl or QWEN_SERVICE_URL; Qwen bypass is forbidden.'
    }
    $qwenBaseUrl = $QwenServiceUrl.TrimEnd('/')
    try {
        $qwenHealth = Invoke-RestMethod -Method Get -Uri "$qwenBaseUrl/health" -TimeoutSec 10
    }
    catch {
        throw "Qwen health check failed at $qwenBaseUrl/health`: $($_.Exception.Message)"
    }
    if ($qwenHealth.status -ne 'READY') {
        throw "Qwen service is not READY: $($qwenHealth | ConvertTo-Json -Compress)"
    }
    if (-not $AllowNonProductionQwen -and $qwenHealth.production_ready -ne $true) {
        throw 'Official evidence requires a production Qwen backend; deterministic test backend is forbidden.'
    }
}

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
            '--qwen-service-url', $qwenBaseUrl,
            '--qwen-mode', $QwenMode,
            '--qwen-timeout-ms', [string]$QwenTimeoutMs,
            '--qwen-queue-size', '1',
            '--qwen-image-root', $projectRoot,
            '--qwen-image-prefix', 'artifacts/runtime/qwen_official',
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


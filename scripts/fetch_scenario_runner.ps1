param(
    [string]$Target = (Join-Path $PSScriptRoot "..\external\scenario_runner")
)

$ErrorActionPreference = "Stop"
$Url = "https://github.com/carla-simulator/scenario_runner.git"
$Commit = "94ff3b8af752bad2b9d464ad5105868906aa34c0"
$Target = [System.IO.Path]::GetFullPath($Target)

if (-not (Test-Path -LiteralPath $Target)) {
    git clone --filter=blob:none $Url $Target
}

$Origin = (git -C $Target remote get-url origin).Trim()
if ($Origin -ne $Url) {
    throw "Unexpected ScenarioRunner origin: $Origin"
}
git -C $Target fetch --tags origin
git -C $Target checkout --detach $Commit
$Actual = (git -C $Target rev-parse HEAD).Trim()
if ($Actual -ne $Commit) {
    throw "ScenarioRunner commit mismatch: expected $Commit, got $Actual"
}
Write-Output "ScenarioRunner v0.9.16 pinned at $Actual"

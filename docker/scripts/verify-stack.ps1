[CmdletBinding()]
param(
    [string]$ComposeFile = "docker/compose.yaml",
    [switch]$BuildController,
    [switch]$StartCarla
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

docker version --format '{{.Server.Version}}'
if ($LASTEXITCODE -ne 0) { throw "Docker Desktop is not available." }

$envFile = if (Test-Path "docker/.env") { "docker/.env" } else { "docker/.env.example" }
docker compose --env-file $envFile -f $ComposeFile config --quiet
if ($LASTEXITCODE -ne 0) { throw "Compose configuration validation failed." }

if ($BuildController) {
    docker compose --env-file $envFile -f $ComposeFile --profile controller build controller
    if ($LASTEXITCODE -ne 0) { throw "Controller image build failed." }
}

if ($StartCarla) {
    docker compose --env-file $envFile -f $ComposeFile up -d carla
    if ($LASTEXITCODE -ne 0) { throw "CARLA container did not start." }
    docker compose --env-file $envFile -f $ComposeFile ps
}

Write-Host "Docker configuration validation passed."

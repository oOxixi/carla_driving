[CmdletBinding()]
param(
    [string]$ControllerImage = "carla-driving-controller:0.1.0",
    [string]$CarlaImage = "carlasim/carla:0.9.16",
    [string]$OutputDirectory = "artifacts",
    [switch]$IncludeCarla
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$outputPath = Join-Path $repoRoot $OutputDirectory
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

$images = @($ControllerImage)
if ($IncludeCarla) { $images += $CarlaImage }
foreach ($image in $images) {
    docker image inspect $image *> $null
    if ($LASTEXITCODE -ne 0) { throw "Local image not found: $image. Build/pull it before export." }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archive = Join-Path $outputPath "carla-driving-images-$stamp.tar"
docker image save --output $archive @images
if ($LASTEXITCODE -ne 0) { throw "docker image save failed." }

$hash = (Get-FileHash -Algorithm SHA256 $archive).Hash
Set-Content -Encoding ascii -Path "$archive.sha256" -Value "$hash  $([IO.Path]::GetFileName($archive))"
Write-Host "Export complete: $archive"
Write-Host "SHA256: $hash"

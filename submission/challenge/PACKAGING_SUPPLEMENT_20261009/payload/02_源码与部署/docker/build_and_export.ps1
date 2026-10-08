param([string]$ImageName = 'challenge-student-x86:20261008')
$ErrorActionPreference = 'Stop'
$packageRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$dockerExe = (Get-Command docker -ErrorAction Stop).Source
$baseRef = 'openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1'
$exportDir = Join-Path $PSScriptRoot ('exports/' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
function Invoke-DockerChecked {
  param([string[]]$DockerArgs, [string]$LogPath)
  $savedPreference = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $rawOutput = & $dockerExe @DockerArgs 2>&1
    $dockerStatus = $LASTEXITCODE
  } finally { $ErrorActionPreference = $savedPreference }
  $lines = @($rawOutput | ForEach-Object { $_.ToString() })
  if ($LogPath) { $lines | Set-Content -LiteralPath $LogPath -Encoding utf8 }
  if ($dockerStatus -ne 0) { throw "Docker step failed ($dockerStatus): $($DockerArgs -join ' '). $($lines -join [Environment]::NewLine)" }
  return ($lines -join [Environment]::NewLine)
}
Push-Location $packageRoot
try {
  $null = Invoke-DockerChecked -DockerArgs @('info')
  $baseInspect = Invoke-DockerChecked -DockerArgs @('image','inspect',$baseRef)
  $baseObject = @($baseInspect | ConvertFrom-Json)[0]
  if ($baseObject.Architecture -ne 'amd64' -or $baseObject.Os -ne 'linux') { throw 'Expected Linux amd64 OE base image.' }
  New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
  $baseInspect | Set-Content -LiteralPath (Join-Path $exportDir 'base_image_inspect.json') -Encoding utf8
  $null = Invoke-DockerChecked -DockerArgs @('build','--platform','linux/amd64','--build-arg',"BASE_IMAGE=$baseRef",'-f','02_源码与部署/docker/Dockerfile.student-x86','-t',$ImageName,'.') -LogPath (Join-Path $exportDir 'build.log')
  $null = Invoke-DockerChecked -DockerArgs @('run','--rm','--entrypoint','python3',$ImageName,'/opt/challenge/02_源码与部署/docker/verify_runtime.py') -LogPath (Join-Path $exportDir 'runtime_dependencies.json')
  $null = Invoke-DockerChecked -DockerArgs @('run','--rm','--entrypoint','python3',$ImageName,'-m','pip','freeze','--all') -LogPath (Join-Path $exportDir 'runtime_freeze.txt')
  $imageInspect = Invoke-DockerChecked -DockerArgs @('image','inspect',$ImageName) -LogPath (Join-Path $exportDir 'image_inspect.json')
  $imageObject = @($imageInspect | ConvertFrom-Json)[0]
  $archivePath = Join-Path $exportDir 'student-x86-image.tar'
  $null = Invoke-DockerChecked -DockerArgs @('save','--output',$archivePath,$ImageName) -LogPath (Join-Path $exportDir 'save.log')
  $archive = Get-Item -LiteralPath $archivePath
  if ($archive.Length -le 0) { throw 'Docker save produced an empty archive.' }
  $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
  "$archiveHash  student-x86-image.tar" | Set-Content -LiteralPath (Join-Path $exportDir 'image_sha256.txt') -Encoding utf8
  [ordered]@{
    status='BUILT_VERIFIED_EXPORTED'; generated_at_utc=(Get-Date).ToUniversalTime().ToString('o');
    image_ref=$ImageName; image_id=$imageObject.Id; repo_digests=@($imageObject.RepoDigests);
    base_ref=$baseRef; base_image_id=$baseObject.Id; base_repo_digests=@($baseObject.RepoDigests);
    archive_file='student-x86-image.tar'; archive_bytes=$archive.Length; archive_sha256=$archiveHash;
    model_inference_run=$false; registry_published=$false;
    dependency_lock_scope='B3 direct versions; PyYAML range; transitive versions in runtime_freeze.txt'
  } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $exportDir 'image_manifest.json') -Encoding utf8
  Write-Output "Built and exported: $exportDir"
} finally { Pop-Location }


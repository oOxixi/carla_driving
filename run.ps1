param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('preflight','smoke','evaluate','demo','stability')][string]$Mode,
    [ValidateSet('rtx5070','a800-safe','a800-optimized')][string]$Profile = 'rtx5070',
    [string]$EvaluateRun
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Engine is unavailable' }
$base = @('compose','--project-directory',$root,'--env-file',(Join-Path $root "config/repro/$Profile.env"),'-f',(Join-Path $root 'docker/compose.yaml'))
& docker @base config --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& docker @base up -d --wait carla qwen
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$bootstrap = Join-Path $root 'output/bootstrap'
New-Item -ItemType Directory -Force $bootstrap | Out-Null
& docker @base logs --no-color --no-log-prefix qwen | Set-Content -Encoding utf8 (Join-Path $bootstrap 'qwen.log')
& docker @base logs --no-color --no-log-prefix carla | Set-Content -Encoding utf8 (Join-Path $bootstrap 'carla.log')
$cli = @('run','--rm','controller','python3','-m','tools.repro_cli',$Mode,'--profile',$Profile,
    '--data-root','/app/release_data','--output-root','/output',
    '--qwen-log','/output/bootstrap/qwen.log','--carla-log','/output/bootstrap/carla.log')
if ($EvaluateRun) { $cli += @('--evaluate-run',$EvaluateRun) }
& docker @base @cli
exit $LASTEXITCODE

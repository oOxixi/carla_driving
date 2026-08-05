param([ValidateSet('rtx5070','a800-safe','a800-optimized')][string]$Profile = 'rtx5070')
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
& docker compose --project-directory $root --env-file (Join-Path $root "config/repro/$Profile.env") -f (Join-Path $root 'docker/compose.yaml') down
exit $LASTEXITCODE

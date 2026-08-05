#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:?usage: ./run.sh MODE [--profile PROFILE]}"; shift
profile="rtx5070"
if [[ "${1:-}" == "--profile" ]]; then profile="${2:?--profile requires a value}"; shift 2; fi
case "$profile" in rtx5070|a800-safe|a800-optimized) ;; *) echo "unsupported profile: $profile" >&2; exit 2;; esac
command -v docker >/dev/null || { echo "Docker is required" >&2; exit 1; }
docker info >/dev/null
compose=(docker compose --project-directory "$root" --env-file "$root/config/repro/$profile.env" -f "$root/docker/compose.yaml")
"${compose[@]}" config --quiet
"${compose[@]}" up -d --wait carla qwen
mkdir -p "$root/output/bootstrap"
"${compose[@]}" logs --no-color --no-log-prefix qwen > "$root/output/bootstrap/qwen.log"
"${compose[@]}" logs --no-color --no-log-prefix carla > "$root/output/bootstrap/carla.log"
exec "${compose[@]}" run --rm controller python3 -m tools.repro_cli "$mode" \
  --profile "$profile" --data-root /app/release_data --output-root /output \
  --qwen-log /output/bootstrap/qwen.log --carla-log /output/bootstrap/carla.log "$@"

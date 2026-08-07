#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
profile="${REPRO_PROFILE:-rtx5070}"
case "$profile" in rtx5070|a800-safe|a800-optimized) ;; *) echo "unsupported profile: $profile" >&2; exit 2;; esac
exec docker compose --project-directory "$root" --env-file "$root/config/repro/$profile.env" -f "$root/docker/compose.yaml" down

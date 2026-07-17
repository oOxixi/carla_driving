#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${CONTROLLER_COMMAND:-}" ]]; then
  echo "[controller] executing CONTROLLER_COMMAND"
  exec bash -lc "$CONTROLLER_COMMAND"
fi

exec "$@"

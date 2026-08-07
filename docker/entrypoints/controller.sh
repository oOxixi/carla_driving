#!/usr/bin/env bash
set -euo pipefail

python3 /app/tools/verify_model_manifest.py \
  --manifest /models/model_manifest.json \
  --profile sensevoice-small \
  --root /models/asr/SenseVoiceSmall
python3 /app/tools/verify_model_manifest.py \
  --manifest /models/model_manifest.json \
  --profile sensevoice-dialect-lora \
  --root /app/voice_group/lora_dialect

if [[ -n "${CONTROLLER_COMMAND:-}" ]]; then
  echo "[controller] executing CONTROLLER_COMMAND"
  exec bash -lc "$CONTROLLER_COMMAND"
fi

exec "$@"

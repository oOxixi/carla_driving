#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "${ROOT_DIR}"

source .venv/bin/activate

python challenge/runtime/student_x86.py \
    --model challenge/student_v0_fp32.onnx \
    --warmup 5 \
    --runs 20 \
    --profile-output challenge/runtime/runtime_profile_x86.json

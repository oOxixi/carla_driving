#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: perception/fault_injection.sh INPUT.jsonl OUTPUT.jsonl FAULT [extra args...]" >&2
  exit 2
fi

input_path=$1
output_path=$2
fault_name=$3
shift 3

python -m perception.fault_injection \
  --input "${input_path}" \
  --output "${output_path}" \
  --fault "${fault_name}" \
  "$@"

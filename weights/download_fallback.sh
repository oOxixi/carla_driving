#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${RELEASE_WEIGHTS_DIR:-$(cd "$script_dir/.." && pwd)/release_assets/weights}"
mkdir -p "$root"
revision="f91db2369bd00e7ec20bf09b6a0080cdb26aefa5"
partial="$root/.partial"
[[ ! -e "$partial" ]] || { echo "partial directory already exists: $partial" >&2; exit 2; }
command -v huggingface-cli >/dev/null || { echo "huggingface-cli is required for network fallback" >&2; exit 2; }
huggingface-cli download h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4 --revision "$revision" --local-dir "$partial"
printf '%s\n' "$revision" > "$partial/REVISION"
mv "$partial" "$root/qwen3vl-2b-int4"

#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${RELEASE_WEIGHTS_DIR:-$(cd "$script_dir/.." && pwd)/release_assets/weights}/optional"
mkdir -p "$root"
case "${1:-}" in
  qwen3vl-2b-fp8) model="Qwen/Qwen3-VL-2B-Instruct-FP8"; revision="46485250d8854c0a9be4f1adbc67ca47e5bb6fa5" ;;
  qwen25vl-3b-bf16) model="Qwen/Qwen2.5-VL-3B-Instruct"; revision="66285546d2b821cf421d4f5eb2576359d3770cd3" ;;
  qwen25vl-7b-awq) model="Qwen/Qwen2.5-VL-7B-Instruct-AWQ"; revision="536a35794df8831aa814970ee8f89eff577e7718" ;;
  *) echo "usage: $0 qwen3vl-2b-fp8|qwen25vl-3b-bf16|qwen25vl-7b-awq" >&2; exit 2 ;;
esac
partial="$root/.partial-$1"
[[ ! -e "$partial" ]] || { echo "partial directory already exists: $partial" >&2; exit 2; }
command -v huggingface-cli >/dev/null || { echo "huggingface-cli is required" >&2; exit 2; }
huggingface-cli download "$model" --revision "$revision" --local-dir "$partial"
printf '%s\n' "$revision" > "$partial/REVISION"
mv "$partial" "$root/$1"

#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="${RELEASE_WEIGHTS_DIR:-$(cd "$script_dir/.." && pwd)/release_assets/weights}/asr"
mkdir -p "$root"
revision="7bf452403abd7353a300cd760f7adae7701c92c1"
partial="$root/.partial-asr"
[[ ! -e "$partial" ]] || { echo "partial directory already exists: $partial" >&2; exit 2; }
command -v modelscope >/dev/null || { echo "modelscope CLI is required for ASR fallback" >&2; exit 2; }
modelscope download --model iic/SenseVoiceSmall --revision "$revision" --local_dir "$partial"
printf '%s\n' "$revision" > "$partial/REVISION"
mv "$partial" "$root/SenseVoiceSmall"

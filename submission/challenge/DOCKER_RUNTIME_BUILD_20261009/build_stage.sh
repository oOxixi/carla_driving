#!/usr/bin/env bash
# Build/export an actual runtime-only image. No private Student model is uploaded.
set -euo pipefail
: "${OUT_DIR:?OUT_DIR must name the workflow artifact directory}"
: "${STAGE_IMAGE:?STAGE_IMAGE is required}"
: "${RESOLVED_BASE:?Registry preflight must resolve the immutable base first}"
: "${MAX_IMAGE_BYTES:=21474836480}"
task_context="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUT_DIR"

record_exit() {
  task_exit_status=$?
  TASK_EXIT_STATUS="$task_exit_status" python3 - <<'PY'
from datetime import datetime, timezone
import json, os
from pathlib import Path
target = Path(os.environ['OUT_DIR']) / 'build_status.json'
status = int(os.environ['TASK_EXIT_STATUS'])
target.write_text(json.dumps({
    'status': 'RUNTIME_STAGE_EXPORTED' if status == 0 else 'RUNTIME_STAGE_BUILD_FAILED',
    'exit_code': status,
    'generated_at_utc': datetime.now(timezone.utc).isoformat(),
    'stage_image': os.environ['STAGE_IMAGE'],
    'resolved_base': os.environ['RESOLVED_BASE'],
    'private_model_files_included': False,
    'final_student_image_built': False,
    'model_inference_run': False,
}, indent=2) + '\n', encoding='utf-8')
PY
  exit "$task_exit_status"
}
trap record_exit EXIT

python3 "$task_context/verify_context.py" "$task_context" \
  > "$OUT_DIR/public_context_check.json"
docker pull --platform linux/amd64 "$RESOLVED_BASE" \
  2>&1 | tee "$OUT_DIR/pull.log"
docker image inspect "$RESOLVED_BASE" > "$OUT_DIR/base_image_inspect.json"
docker run --rm --entrypoint cat "$RESOLVED_BASE" /etc/os-release \
  > "$OUT_DIR/base_os_release.txt" 2> "$OUT_DIR/base_os_release.log"
docker run --rm --entrypoint python3 "$RESOLVED_BASE" -c \
  'import json,platform; print(json.dumps({"python":platform.python_version(),"machine":platform.machine(),"platform":platform.platform()}))' \
  > "$OUT_DIR/base_runtime.json" 2> "$OUT_DIR/base_runtime.log"
df -B1 "$OUT_DIR" /var/lib/docker > "$OUT_DIR/disk_after_pull.txt"
docker build --platform linux/amd64 --progress plain \
  --build-arg "BASE_IMAGE=$RESOLVED_BASE" \
  -f "$task_context/Dockerfile.stage" -t "$STAGE_IMAGE" "$task_context" \
  2>&1 | tee "$OUT_DIR/build.log"

docker run --rm --entrypoint python3 "$STAGE_IMAGE" \
  /opt/challenge/02_源码与部署/docker/verify_runtime_stage.py \
  > "$OUT_DIR/runtime_dependencies.json" 2> "$OUT_DIR/runtime_verify.log"
docker run --rm --entrypoint python3 "$STAGE_IMAGE" \
  /opt/challenge/02_源码与部署/scripts/check_deployment.py --profile files \
  > "$OUT_DIR/deployment_files_check.json" 2> "$OUT_DIR/deployment_files_check.log"
docker run --rm --entrypoint python3 "$STAGE_IMAGE" \
  /opt/challenge/02_源码与部署/scripts/check_deployment.py --profile student \
  > "$OUT_DIR/deployment_import_check.json" 2> "$OUT_DIR/deployment_import_check.log"
docker run --rm --entrypoint python3 "$STAGE_IMAGE" -m pip freeze --all \
  > "$OUT_DIR/runtime_freeze.txt" 2> "$OUT_DIR/runtime_freeze.log"
docker run --rm --entrypoint dpkg-query "$STAGE_IMAGE" -W \
  > "$OUT_DIR/os_packages.txt" 2> "$OUT_DIR/os_packages.log"
docker image inspect "$STAGE_IMAGE" > "$OUT_DIR/image_inspect.json"
python3 "$task_context/record_stage_metadata.py" --output "$OUT_DIR" \
  --max-image-bytes "$MAX_IMAGE_BYTES" --before-save

# Stream directly to gzip. Do not allocate an extra uncompressed image archive.
docker save "$STAGE_IMAGE" 2> "$OUT_DIR/save.log" \
  | gzip -1 > "$OUT_DIR/runtime-stage-image.tar.gz"
gzip -t "$OUT_DIR/runtime-stage-image.tar.gz"
python3 "$task_context/record_stage_metadata.py" --output "$OUT_DIR" \
  --max-image-bytes "$MAX_IMAGE_BYTES"
df -B1 "$OUT_DIR" /var/lib/docker > "$OUT_DIR/disk_after_save.txt"

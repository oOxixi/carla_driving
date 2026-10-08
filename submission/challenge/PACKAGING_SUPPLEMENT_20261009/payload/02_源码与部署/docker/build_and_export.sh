#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-challenge-student-x86:20261008}"
BASE_REF='openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1'
command -v docker >/dev/null
docker info >/dev/null
BASE_ID=$(docker image inspect --format '{{.Id}}' "$BASE_REF")
test "$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$BASE_REF")" = linux/amd64
EXPORT_DIR="$SCRIPT_DIR/exports/$(date -u +%Y%m%d_%H%M%S)_$$"
cd "$PACKAGE_ROOT"
mkdir -p "$EXPORT_DIR"
docker image inspect "$BASE_REF" > "$EXPORT_DIR/base_image_inspect.json"
docker build --platform linux/amd64 --build-arg "BASE_IMAGE=$BASE_REF" \
  -f 02_源码与部署/docker/Dockerfile.student-x86 -t "$IMAGE_NAME" . 2>&1 | tee "$EXPORT_DIR/build.log"
docker run --rm --entrypoint python3 "$IMAGE_NAME" \
  /opt/challenge/02_源码与部署/docker/verify_runtime.py > "$EXPORT_DIR/runtime_dependencies.json"
docker run --rm --entrypoint python3 "$IMAGE_NAME" -m pip freeze --all > "$EXPORT_DIR/runtime_freeze.txt"
docker image inspect "$IMAGE_NAME" > "$EXPORT_DIR/image_inspect.json"
docker save -o "$EXPORT_DIR/student-x86-image.tar" "$IMAGE_NAME" 2> "$EXPORT_DIR/save.log"
test -s "$EXPORT_DIR/student-x86-image.tar"
ARCHIVE_HASH=$(sha256sum "$EXPORT_DIR/student-x86-image.tar" | cut -d ' ' -f 1)
printf '%s  student-x86-image.tar\n' "$ARCHIVE_HASH" > "$EXPORT_DIR/image_sha256.txt"
docker run --rm --entrypoint python3 -v "$EXPORT_DIR:/export" "$IMAGE_NAME" -c '
import datetime,json,pathlib
p=pathlib.Path("/export")
image=json.loads((p/"image_inspect.json").read_text())[0]
base=json.loads((p/"base_image_inspect.json").read_text())[0]
manifest={"status":"BUILT_VERIFIED_EXPORTED", "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"image_ref":image["RepoTags"][0],"image_id":image["Id"],"repo_digests":image.get("RepoDigests",[]),
"base_ref":"openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1","base_image_id":base["Id"],"base_repo_digests":base.get("RepoDigests",[]),
"archive_file":"student-x86-image.tar","archive_bytes":(p/"student-x86-image.tar").stat().st_size,
"archive_sha256":(p/"image_sha256.txt").read_text().split()[0],"model_inference_run":False,"registry_published":False,
"dependency_lock_scope":"B3 direct versions; PyYAML range; transitive versions in runtime_freeze.txt"}
(p/"image_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")'
printf 'Built and exported: %s\n' "$EXPORT_DIR"

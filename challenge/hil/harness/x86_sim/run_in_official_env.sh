#!/usr/bin/env bash
# Run a command inside the official X86 image (OpenExplorer 3.9.1) with the repo
# mounted at /repo, so B3 measurements can be taken in the official environment.
#
# Usage: run_in_official_env.sh [--recreate] -- "<command>"
#   --recreate  rebuild the sibling container (e.g. after changing the mounts)
set -u

REPO_HOST=/mnt/d/nana/carla_driving-new/carla_driving-new
OE_HOST=/mnt/d/nana/oe/horizon_j6_open_explorer_v3.9.1-py310_20260821
WORK_HOST=/mnt/d/nana/oe/work
DATA_HOST=/mnt/d/nana/oe/dataset
IMAGE=openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1
NAME=b3_oe_repo

recreate=0
if [ "${1:-}" = "--recreate" ]; then recreate=1; shift; fi
if [ "${1:-}" = "--" ]; then shift; fi

if [ "$recreate" = "1" ] || ! docker inspect "$NAME" >/dev/null 2>&1; then
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker run -d --name "$NAME" \
    -v "$OE_HOST":/open_explorer \
    -v "$WORK_HOST":/work \
    -v "$DATA_HOST":/data/horizon_j6/data \
    -v "$REPO_HOST":/repo \
    "$IMAGE" sleep infinity >/dev/null
  echo "created container $NAME (repo -> /repo)"
else
  docker start "$NAME" >/dev/null 2>&1 || true
fi

docker exec -w /repo "$NAME" bash -lc "$*"

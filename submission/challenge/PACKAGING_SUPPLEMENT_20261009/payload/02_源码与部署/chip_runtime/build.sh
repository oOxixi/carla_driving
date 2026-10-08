#!/usr/bin/env bash
set -euo pipefail
TASK_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${OE_DIR:?Set OE_DIR to OpenExplorer 3.9.1 unpacked directory}"
: "${ARM_TOOLCHAIN_BIN:?Set ARM_TOOLCHAIN_BIN to aarch64-none-linux-gnu compiler bin}"
cmake -S "$TASK_DIR" -B "$TASK_DIR/build_arm" \
  -DCMAKE_TOOLCHAIN_FILE="$TASK_DIR/cmake/aarch64.cmake" \
  -DUCP_ROOT="$OE_DIR/samples/ucp_tutorial/deps_aarch64/ucp" \
  -DCMAKE_BUILD_TYPE=Release
cmake --build "$TASK_DIR/build_arm" --parallel 4

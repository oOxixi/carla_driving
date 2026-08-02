#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
runtime_dir="${project_root}/artifacts/second_group_20260731/runtime"
pid_file="${runtime_dir}/qwen_service.pid"
service_log="${runtime_dir}/qwen_service.log"
health_json="${runtime_dir}/healthcheck.json"
python_bin=${PYTHON_BIN:-python}
qwen_host=${QWEN_HOST:-127.0.0.1}
qwen_port=${QWEN_PORT:-8765}
qwen_url="http://${qwen_host}:${qwen_port}"
qwen_image_root=${QWEN_IMAGE_ROOT:-${project_root}}
qwen_image_prefix=${QWEN_IMAGE_PREFIX:-artifacts/second_group_20260731/qwen_images}

mkdir -p "${runtime_dir}"

qwen_pid() {
  if [[ ! -s "${pid_file}" ]]; then
    return 1
  fi
  local pid
  pid=$(<"${pid_file}")
  [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
  kill -0 "${pid}" 2>/dev/null || return 1
  local command_line
  command_line=$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)
  [[ "${command_line}" == *"qwen_service.server"* ]] || return 1
  printf '%s\n' "${pid}"
}

start_qwen() {
  if qwen_pid >/dev/null; then
    echo "Qwen service already running: pid=$(qwen_pid)"
    return 0
  fi
  local model_args=()
  if [[ -n "${QWEN_MODEL_PATH:-}" ]]; then
    model_args+=(--model-path "${QWEN_MODEL_PATH}")
    model_args+=(--image-root "${qwen_image_root}")
  elif [[ "${QWEN_TEST_BACKEND:-0}" == "1" ]]; then
    model_args+=(--deterministic-test-backend)
    echo "WARNING: deterministic Qwen backend is for contract tests only"
  else
    echo "WARNING: no QWEN_MODEL_PATH; slow path will report DEGRADED and fail closed"
  fi
  (
    cd "${project_root}"
    nohup "${python_bin}" -m qwen_service.server \
      --host "${qwen_host}" --port "${qwen_port}" \
      --timeout-ms "${QWEN_TIMEOUT_MS:-300}" \
      --max-concurrency "${QWEN_MAX_CONCURRENCY:-1}" \
      "${model_args[@]}" >"${service_log}" 2>&1 &
    printf '%s\n' "$!" >"${pid_file}"
  )
  local attempts=0
  until qwen_pid >/dev/null || [[ ${attempts} -ge 30 ]]; do
    attempts=$((attempts + 1))
    sleep 0.1
  done
  if ! qwen_pid >/dev/null; then
    echo "Qwen service failed to start; inspect ${service_log}" >&2
    return 1
  fi
  echo "Qwen service started: pid=$(qwen_pid), log=${service_log}"
}

stop_qwen() {
  local pid
  if ! pid=$(qwen_pid); then
    : >"${pid_file}"
    echo "Qwen service is not running"
    return 0
  fi
  kill "${pid}"
  local attempts=0
  while kill -0 "${pid}" 2>/dev/null && [[ ${attempts} -lt 50 ]]; do
    attempts=$((attempts + 1))
    sleep 0.1
  done
  if kill -0 "${pid}" 2>/dev/null; then
    echo "Qwen service did not stop within 5 seconds: pid=${pid}" >&2
    return 1
  fi
  : >"${pid_file}"
  echo "Qwen service stopped: pid=${pid}"
}

healthcheck() {
  local strict=${1:-0}
  local flags=()
  if [[ "${strict}" == "1" ]]; then
    flags+=(--require-qwen --require-carla)
  fi
  (
    cd "${project_root}"
    "${python_bin}" -m runtime.healthcheck \
      --qwen-url "${qwen_url}" \
      --carla-host "${CARLA_HOST:-127.0.0.1}" \
      --carla-port "${CARLA_PORT:-2000}" \
      --output "${health_json}" \
      "${flags[@]}"
  )
}

usage() {
  echo "usage: $0 {start|stop|status|check|strict-check|run} [carla_runner args...]"
  echo "env: PYTHON_BIN, QWEN_MODEL_PATH, QWEN_IMAGE_ROOT, QWEN_IMAGE_PREFIX, QWEN_TEST_BACKEND=1, CARLA_HOST, CARLA_PORT"
}

command=${1:-}
if [[ -z "${command}" ]]; then
  usage
  exit 2
fi
shift

case "${command}" in
  start)
    start_qwen
    healthcheck 0
    ;;
  stop)
    stop_qwen
    ;;
  status)
    if qwen_pid >/dev/null; then
      echo "Qwen service running: pid=$(qwen_pid)"
    else
      echo "Qwen service stopped"
    fi
    healthcheck 0
    ;;
  check)
    healthcheck 0
    ;;
  strict-check)
    healthcheck 1
    ;;
  run)
    started_here=0
    if ! qwen_pid >/dev/null; then
      start_qwen
      started_here=1
    fi
    cleanup() {
      if [[ "${started_here}" == "1" ]]; then
        stop_qwen || true
      fi
    }
    trap cleanup EXIT INT TERM
    healthcheck 0
    (
      cd "${project_root}"
      "${python_bin}" -m integration.carla_runner \
        --host "${CARLA_HOST:-127.0.0.1}" \
        --port "${CARLA_PORT:-2000}" \
        --qwen-service-url "${qwen_url}" \
        --qwen-timeout-ms "${QWEN_TIMEOUT_MS:-300}" \
        --qwen-image-root "${qwen_image_root}" \
        --qwen-image-prefix "${qwen_image_prefix}" \
        "$@"
    )
    ;;
  *)
    usage
    exit 2
    ;;
esac

# run_full_pipeline：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[scripts/run_full_pipeline.sh](../../../scripts/run_full_pipeline.sh)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

run_full_pipeline

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

入口相关声明（cwd、参数、环境、模块调用、容器指令）；仅用于定位，需结合模块说明判断当前可用性：

- 第 4 行：`project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)`
- 第 5 行：`runtime_dir="${project_root}/artifacts/runtime/full_pipeline"`
- 第 6 行：`pid_file="${runtime_dir}/qwen_service.pid"`
- 第 7 行：`service_log="${runtime_dir}/qwen_service.log"`
- 第 8 行：`health_json="${runtime_dir}/healthcheck.json"`
- 第 9 行：`python_bin=${PYTHON_BIN:-python}`
- 第 10 行：`qwen_host=${QWEN_HOST:-127.0.0.1}`
- 第 11 行：`qwen_port=${QWEN_PORT:-8765}`
- 第 12 行：`qwen_url="http://${qwen_host}:${qwen_port}"`
- 第 13 行：`qwen_image_root=${QWEN_IMAGE_ROOT:-${project_root}}`
- 第 14 行：`qwen_image_prefix=${QWEN_IMAGE_PREFIX:-artifacts/runtime/qwen_images}`
- 第 16 行：`mkdir -p "${runtime_dir}"`
- 第 19 行：`if [[ ! -s "${pid_file}" ]]; then`
- 第 23 行：`pid=$(<"${pid_file}")`
- 第 24 行：`[[ "${pid}" =~ ^[0-9]+$ ]] || return 1`
- 第 25 行：`kill -0 "${pid}" 2>/dev/null || return 1`
- 第 27 行：`command_line=$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)`
- 第 28 行：`[[ "${command_line}" == *"qwen_service.server"* ]] || return 1`
- 第 29 行：`printf '%s\n' "${pid}"`
- 第 38 行：`if [[ -n "${QWEN_MODEL_PATH:-}" ]]; then`
- 第 39 行：`model_args+=(--model-path "${QWEN_MODEL_PATH}")`
- 第 40 行：`model_args+=(--image-root "${qwen_image_root}")`
- 第 41 行：`elif [[ "${QWEN_TEST_BACKEND:-0}" == "1" ]]; then`
- 第 48 行：`cd "${project_root}"`
- 第 49 行：`nohup "${python_bin}" -m qwen_service.server \`
- 第 50 行：`--host "${qwen_host}" --port "${qwen_port}" \`
- 第 51 行：`--timeout-ms "${QWEN_TIMEOUT_MS:-300}" \`
- 第 52 行：`--max-concurrency "${QWEN_MAX_CONCURRENCY:-1}" \`
- 第 53 行：`"${model_args[@]}" >"${service_log}" 2>&1 &`
- 第 54 行：`printf '%s\n' "$!" >"${pid_file}"`
- 第 57 行：`until qwen_pid >/dev/null || [[ ${attempts} -ge 30 ]]; do`
- 第 62 行：`echo "Qwen service failed to start; inspect ${service_log}" >&2`
- 第 65 行：`echo "Qwen service started: pid=$(qwen_pid), log=${service_log}"`
- 第 71 行：`: >"${pid_file}"`
- 第 75 行：`kill "${pid}"`
- 第 77 行：`while kill -0 "${pid}" 2>/dev/null && [[ ${attempts} -lt 50 ]]; do`
- 第 81 行：`if kill -0 "${pid}" 2>/dev/null; then`
- 第 82 行：`echo "Qwen service did not stop within 5 seconds: pid=${pid}" >&2`
- 第 85 行：`: >"${pid_file}"`
- 第 86 行：`echo "Qwen service stopped: pid=${pid}"`
- 第 90 行：`local strict=${1:-0}`
- 第 92 行：`if [[ "${strict}" == "1" ]]; then`
- 第 96 行：`cd "${project_root}"`
- 第 97 行：`"${python_bin}" -m runtime.healthcheck \`
- 第 98 行：`--qwen-url "${qwen_url}" \`
- 第 99 行：`--carla-host "${CARLA_HOST:-127.0.0.1}" \`
- 第 100 行：`--carla-port "${CARLA_PORT:-2000}" \`
- 第 101 行：`--output "${health_json}" \`
- 第 102 行：`"${flags[@]}"`
- 第 111 行：`command=${1:-}`
- 第 112 行：`if [[ -z "${command}" ]]; then`
- 第 118 行：`case "${command}" in`
- 第 147 行：`if [[ "${started_here}" == "1" ]]; then`
- 第 154 行：`cd "${project_root}"`
- 第 155 行：`"${python_bin}" -m integration.carla_runner \`
- 第 156 行：`--host "${CARLA_HOST:-127.0.0.1}" \`
- 第 157 行：`--port "${CARLA_PORT:-2000}" \`
- 第 158 行：`--qwen-service-url "${qwen_url}" \`
- 第 159 行：`--qwen-timeout-ms "${QWEN_TIMEOUT_MS:-300}" \`
- 第 160 行：`--qwen-image-root "${qwen_image_root}" \`
- 第 161 行：`--qwen-image-prefix "${qwen_image_prefix}" \`

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `scripts/run_full_pipeline.sh`

来源 SHA256：`9aebae2837e7bc33e67d41c0ec925ad1fad95fa548a39aa2418615fd872a0169`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。

### 脚本参数与转发原文

以下摘录参数声明、变量默认及参数转发位置；赋值变量不全是外部CLI。Shell环境fallback与PowerShell param类型由脚本解释，不套用argparse规则。未执行脚本。

```bash
# L4
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# L5
runtime_dir="${project_root}/artifacts/runtime/full_pipeline"
# L6
pid_file="${runtime_dir}/qwen_service.pid"
# L7
service_log="${runtime_dir}/qwen_service.log"
# L8
health_json="${runtime_dir}/healthcheck.json"
# L9
python_bin=${PYTHON_BIN:-python}
# L10
qwen_host=${QWEN_HOST:-127.0.0.1}
# L11
qwen_port=${QWEN_PORT:-8765}
# L12
qwen_url="http://${qwen_host}:${qwen_port}"
# L13
qwen_image_root=${QWEN_IMAGE_ROOT:-${project_root}}
# L14
qwen_image_prefix=${QWEN_IMAGE_PREFIX:-artifacts/runtime/qwen_images}
# L23
  pid=$(<"${pid_file}")
# L27
  command_line=$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)
# L38
  if [[ -n "${QWEN_MODEL_PATH:-}" ]]; then
# L41
  elif [[ "${QWEN_TEST_BACKEND:-0}" == "1" ]]; then
# L51
      --timeout-ms "${QWEN_TIMEOUT_MS:-300}" \
# L52
      --max-concurrency "${QWEN_MAX_CONCURRENCY:-1}" \
# L58
    attempts=$((attempts + 1))
# L78
    attempts=$((attempts + 1))
# L90
  local strict=${1:-0}
# L99
      --carla-host "${CARLA_HOST:-127.0.0.1}" \
# L100
      --carla-port "${CARLA_PORT:-2000}" \
# L111
command=${1:-}
# L141
    started_here=0
# L144
      started_here=1
# L156
        --host "${CARLA_HOST:-127.0.0.1}" \
# L157
        --port "${CARLA_PORT:-2000}" \
# L159
        --qwen-timeout-ms "${QWEN_TIMEOUT_MS:-300}" \
# L162
        "$@"
```

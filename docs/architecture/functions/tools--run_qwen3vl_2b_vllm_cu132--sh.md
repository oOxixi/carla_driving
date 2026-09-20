# run_qwen3vl_2b_vllm_cu132：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_qwen3vl_2b_vllm_cu132.sh](../../../tools/run_qwen3vl_2b_vllm_cu132.sh)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

run_qwen3vl_2b_vllm_cu132

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

入口相关声明（cwd、参数、环境、模块调用、容器指令）；仅用于定位，需结合模块说明判断当前可用性：

- 第 4 行：`repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"`
- 第 5 行：`variant="${QWEN_MODEL_VARIANT:-int4}"`
- 第 6 行：`venv="${QWEN_VLLM_VENV:-/home/restar/.venvs/carla_qwen3_vllm_cu132}"`
- 第 10 行：`case "${variant}" in`
- 第 12 行：`default_model_path="${repo_root}/models/Qwen3-VL-2B-Instruct-GPTQ-Int4"`
- 第 18 行：`default_model_path="${repo_root}/models/Qwen3-VL-2B-Instruct-FP8"`
- 第 24 行：`echo "QWEN_MODEL_VARIANT must be int4 or fp8; got: ${variant}" >&2`
- 第 29 行：`model_path="${QWEN_MODEL_PATH:-${default_model_path}}"`
- 第 30 行：`served_model="${QWEN_SERVED_MODEL_NAME:-${served_model}}"`
- 第 31 行：`host="${QWEN_HOST:-0.0.0.0}"`
- 第 32 行：`port="${QWEN_PORT:-8001}"`
- 第 34 行：`if [[ ! -x "${venv}/bin/python" || ! -x "${venv}/bin/vllm" ]]; then`
- 第 35 行：`echo "CUDA 13.2 vLLM environment not found: ${venv}" >&2`
- 第 38 行：`if [[ ! -f "${model_path}/config.json" ]]; then`
- 第 39 行：`echo "Qwen model not found: ${model_path}" >&2`
- 第 43 行：`export CUDA_HOME="${QWEN_CUDA_HOME:-${venv}/lib/python3.10/site-packages/nvidia/cu13}"`
- 第 44 行：`export PATH="${CUDA_HOME}/bin:${venv}/bin:${PATH}"`
- 第 48 行：`MODEL_PATH="${model_path}" EXPECTED_QUANT="${expected_quant}" \`
- 第 49 行：`EXPECTED_REVISION="${expected_revision}" "${venv}/bin/python" - <<'PY'`
- 第 94 行：`if [[ "${QWEN_DRY_RUN:-0}" == "1" ]]; then`
- 第 95 行：`echo "dry-run: variant=${variant} model=${served_model} host=${host} port=${port}"`
- 第 99 行：`exec "${venv}/bin/vllm" serve "${model_path}" \`
- 第 100 行：`--served-model-name "${served_model}" \`
- 第 101 行：`"${quant_args[@]}" \`
- 第 102 行：`--host "${host}" \`
- 第 103 行：`--port "${port}" \`
- 第 111 行：`"${graph_args[@]}"`

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

### `tools/run_qwen3vl_2b_vllm_cu132.sh`

来源 SHA256：`067c8a9457728f06b7dd166c929614647b8f2d99e2ea61b0d4e904a093ebbe9b`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。

### 脚本参数与转发原文

以下摘录参数声明、变量默认及参数转发位置；赋值变量不全是外部CLI。Shell环境fallback与PowerShell param类型由脚本解释，不套用argparse规则。未执行脚本。

```bash
# L4
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# L5
variant="${QWEN_MODEL_VARIANT:-int4}"
# L6
venv="${QWEN_VLLM_VENV:-/home/restar/.venvs/carla_qwen3_vllm_cu132}"
# L7
quant_args=()
# L8
graph_args=(-cc.cudagraph_mode=NONE)
# L12
    default_model_path="${repo_root}/models/Qwen3-VL-2B-Instruct-GPTQ-Int4"
# L13
    served_model="h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4"
# L14
    expected_revision="f91db2369bd00e7ec20bf09b6a0080cdb26aefa5"
# L15
    expected_quant="gptq"
# L18
    default_model_path="${repo_root}/models/Qwen3-VL-2B-Instruct-FP8"
# L19
    served_model="Qwen/Qwen3-VL-2B-Instruct-FP8"
# L20
    expected_revision="46485250d8854c0a9be4f1adbc67ca47e5bb6fa5"
# L21
    expected_quant="fp8"
# L29
model_path="${QWEN_MODEL_PATH:-${default_model_path}}"
# L30
served_model="${QWEN_SERVED_MODEL_NAME:-${served_model}}"
# L31
host="${QWEN_HOST:-0.0.0.0}"
# L32
port="${QWEN_PORT:-8001}"
# L43
export CUDA_HOME="${QWEN_CUDA_HOME:-${venv}/lib/python3.10/site-packages/nvidia/cu13}"
# L44
export PATH="${CUDA_HOME}/bin:${venv}/bin:${PATH}"
# L45
export VLLM_USE_V2_MODEL_RUNNER=0
# L46
export CUDNN_FRONTEND_CUDART_LIB_NAME=libcudart.so.13
# L48
MODEL_PATH="${model_path}" EXPECTED_QUANT="${expected_quant}" \
# L49
EXPECTED_REVISION="${expected_revision}" "${venv}/bin/python" - <<'PY'
# L90
    flush=True,
# L94
if [[ "${QWEN_DRY_RUN:-0}" == "1" ]]; then
```

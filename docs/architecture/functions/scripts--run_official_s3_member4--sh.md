# run_official_s3_member4：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[scripts/run_official_s3_member4.sh](../../../scripts/run_official_s3_member4.sh)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

run_official_s3_member4

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

入口相关声明（cwd、参数、环境、模块调用、容器指令）；仅用于定位，需结合模块说明判断当前可用性：

- 第 4 行：`project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`
- 第 5 行：`cd "$project_root"`
- 第 7 行：`python_executable="${PYTHON_EXECUTABLE:-python3}"`
- 第 8 行：`qwen_service_url="${QWEN_SERVICE_URL:-http://127.0.0.1:18000}"`
- 第 11 行：`qwen_model="${QWEN_MODEL:-Qwen/Qwen3.5-2B}"`
- 第 12 行：`carla_host="${CARLA_HOST:-127.0.0.1}"`
- 第 13 行：`carla_port="${CARLA_PORT:-2000}"`
- 第 14 行：`log_dir="${S3_LOG_DIR:-artifacts/logs/official_competition}"`
- 第 15 行：`rgb_detector_model="${RGB_DETECTOR_MODEL:-}"`
- 第 16 行：`mode="${1:---run}"`
- 第 19 行：`if [[ "${qwen_model^^}" != *"2B"* ]]; then`
- 第 77 行：`--qwen-image-root "$project_root"`
- 第 85 行：`"$python_executable" "${arguments[@]}"`
- 第 105 行：`--output "${latest_jsonl%.jsonl}.member4.json"`
- 第 110 行：`"$python_executable" "${validator_args[@]}"`

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

### `scripts/run_official_s3_member4.sh`

来源 SHA256：`019019d574b7af749d0b31baac61f3ffc18d3bbf153c9fae8cdf7a1f9332c61e`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。

### 脚本参数与转发原文

以下摘录参数声明、变量默认及参数转发位置；赋值变量不全是外部CLI。Shell环境fallback与PowerShell param类型由脚本解释，不套用argparse规则。未执行脚本。

```bash
# L4
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# L7
python_executable="${PYTHON_EXECUTABLE:-python3}"
# L8
qwen_service_url="${QWEN_SERVICE_URL:-http://127.0.0.1:18000}"
# L11
qwen_model="${QWEN_MODEL:-Qwen/Qwen3.5-2B}"
# L12
carla_host="${CARLA_HOST:-127.0.0.1}"
# L13
carla_port="${CARLA_PORT:-2000}"
# L14
log_dir="${S3_LOG_DIR:-artifacts/logs/official_competition}"
# L15
rgb_detector_model="${RGB_DETECTOR_MODEL:-}"
# L16
mode="${1:---run}"
# L17
scene_path="scenarios/official_competition/S3_extreme_emergency_6km.json"
# L57
arguments=(
# L87
latest_jsonl="$(
# L94
    key=lambda path: path.stat().st_mtime,
# L95
    reverse=True,
# L103
validator_args=(
```

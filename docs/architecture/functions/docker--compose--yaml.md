# compose：功能记录

上级模块：[模块说明](../modules/support-delivery.md) · 实现：[docker/compose.yaml](../../../docker/compose.yaml)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [运行入口、依赖和产物维护](environment-delivery.md)

## 功能职责与范围

compose

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

配置项摘要（按文件顺序，层级以源文件缩进为准）：

- `name: carla-driving`
- `services:`
- `carla:`
- `image: carla-simulator:0.9.16`
- `container_name: carla-server`
- `working_dir: /home/carla`
- `entrypoint: ["/bin/bash", "-lc"]`
- `command: >-`
- `./CarlaUE4.sh -RenderOffScreen -nosound -quality-level=${CARLA_QUALITY_LEVEL:-Low}`
- `-carla-port=2000`
- `ports:`
- `- "${CARLA_PORT:-2000}:2000"`
- `- "${CARLA_STREAM_PORT:-2001}:2001"`
- `- "${CARLA_TM_PORT:-8000}:8000"`
- `environment:`
- `CARLA_RESOLUTION: ${CARLA_RESOLUTION:-640x360}`
- `gpus: all`
- `ipc: host`
- `healthcheck:`
- `test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/127.0.0.1/2000'"]`
- `interval: 10s`
- `timeout: 5s`
- `retries: 18`
- `start_period: 30s`
- `qwen:`
- `build:`
- `context: ..`
- `dockerfile: docker/Dockerfile.qwen-cu132`
- `image: qwen-vllm-cu132:${QWEN_PROFILE}`
- `container_name: qwen-vllm`
- `environment:`
- `QWEN_PROFILE: ${QWEN_PROFILE}`
- `QWEN_GPU_MEMORY_UTILIZATION: ${QWEN_GPU_MEMORY_UTILIZATION}`
- `QWEN_MAX_MODEL_LEN: ${QWEN_MAX_MODEL_LEN}`
- `QWEN_EXTRA_ARGS: ${QWEN_EXTRA_ARGS}`
- `QWEN_OUTPUT_ROOT: /output/runs`
- `volumes:`
- `- ${OUTPUT_DIR:-./output}:/output`
- `gpus: all`
- `ipc: host`
- `healthcheck:`
- `test: ["CMD-SHELL", "curl --fail --silent http://127.0.0.1:8001/v1/models > /dev/null"]`
- `interval: 10s`
- `timeout: 5s`
- `retries: 18`
- `start_period: 30s`
- `controller:`
- `build:`
- `context: ..`
- `dockerfile: docker/Dockerfile.controller`
- `image: carla-controller:${RELEASE_COMMIT}`
- `container_name: carla-controller`
- `depends_on:`
- `carla:`
- `condition: service_healthy`
- `qwen:`
- `condition: service_healthy`
- `environment:`
- `CARLA_HOST: carla`
- `CARLA_PORT: "2000"`
- `QWEN_BASE_URL: http://qwen:8001/v1`
- `SENSEVOICE_MODEL_PATH: /models/asr/SenseVoiceSmall`
- `SENSEVOICE_LORA_PATH: /app/voice_group/lora_dialect`
- `REPRO_OUTPUT_ROOT: /output/runs`
- `volumes:`
- `- ${OUTPUT_DIR:-./output}:/output`
- `gpus: all`
- `ipc: host`
- `restart: "no"`

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-delivery.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `docker/compose.yaml`

来源 SHA256：`939c2547f2a76167b717ae5fdf6093ad00e8a06f5d92245b0166dbd19f70c4f3`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。

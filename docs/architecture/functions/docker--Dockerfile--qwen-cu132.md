# Dockerfile：功能记录

上级模块：[模块说明](../modules/support-delivery.md) · 实现：[docker/Dockerfile.qwen-cu132](../../../docker/Dockerfile.qwen-cu132)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [运行入口、依赖和产物维护](environment-delivery.md)

## 功能职责与范围

Dockerfile

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

入口相关声明（cwd、参数、环境、模块调用、容器指令）；仅用于定位，需结合模块说明判断当前可用性：

- 第 1 行：`FROM nvidia/cuda:13.2.0-cudnn-runtime-ubuntu24.04@sha256:7a31e9bfb2086e4b1ac08aa8e4718d7860730ecc6a9882d2f1e5ed6239f8ef5b`
- 第 3 行：`RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3 python3-pip curl libnuma1 && rm -rf /var/lib/apt/lists/*`
- 第 4 行：`WORKDIR /srv/qwen`
- 第 5 行：`COPY release_assets/wheelhouse/ /wheelhouse/`
- 第 6 行：`COPY third_party/vllm.lock.json /locks/vllm.lock.json`
- 第 7 行：`COPY third_party/qwen-wheelhouse.lock.json /locks/qwen-wheelhouse.lock.json`
- 第 8 行：`COPY tools/verify_release_lock.py /app/tools/verify_release_lock.py`
- 第 9 行：`COPY tools/generate_wheelhouse_lock.py tools/verify_wheelhouse_lock.py /app/tools/`
- 第 10 行：`COPY docker/requirements-qwen.lock.txt /tmp/requirements-qwen.lock.txt`
- 第 11 行：`RUN python3 /app/tools/verify_release_lock.py --lock /locks/vllm.lock.json --root /wheelhouse --key output_wheel \`
- 第 14 行：`COPY release_assets/weights/qwen3vl-2b-int4/ /models/qwen/`
- 第 15 行：`COPY weights/model_manifest.json /models/model_manifest.json`
- 第 16 行：`COPY tools/verify_model_manifest.py /app/tools/verify_model_manifest.py`
- 第 17 行：`COPY tools/create_qwen_launch_logs.py /app/tools/create_qwen_launch_logs.py`
- 第 18 行：`COPY docker/entrypoints/qwen.sh /usr/local/bin/qwen-entrypoint`
- 第 19 行：`RUN chmod 0555 /usr/local/bin/qwen-entrypoint`
- 第 21 行：`ENTRYPOINT ["/usr/local/bin/qwen-entrypoint"]`

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

### `docker/Dockerfile.qwen-cu132`

来源 SHA256：`6be72e12049cdb943809429e4a65aa14315ff8380358248384635b1a1eb5b6bf`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。

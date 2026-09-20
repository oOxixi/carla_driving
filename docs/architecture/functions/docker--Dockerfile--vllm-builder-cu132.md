# Dockerfile：功能记录

上级模块：[模块说明](../modules/support-delivery.md) · 实现：[docker/Dockerfile.vllm-builder-cu132](../../../docker/Dockerfile.vllm-builder-cu132)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [运行入口、依赖和产物维护](environment-delivery.md)

## 功能职责与范围

Dockerfile

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

入口相关声明（cwd、参数、环境、模块调用、容器指令）；仅用于定位，需结合模块说明判断当前可用性：

- 第 1 行：`FROM nvidia/cuda:13.2.0-devel-ubuntu24.04@sha256:f9492f2eea77fbc3d0c14fa8738f35946b42da72917bf5959d284ca39b4f209a AS input-verify`
- 第 7 行：`RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-dev python3-pip git patch ninja-build cmake && rm -rf /var/lib/apt/lists/*`
- 第 8 行：`WORKDIR /src/vllm`
- 第 9 行：`COPY release_assets/source/vllm-568afb3a13806beb53bb2e6bd518269357b237c0.tar.gz /opt/vllm-provenance/`
- 第 10 行：`COPY docker/patches/vllm-cu132-torch.patch /tmp/vllm-cu132-torch.patch`
- 第 11 行：`COPY release_assets/wheelhouse-build/ /wheelhouse-build/`
- 第 12 行：`COPY third_party/vllm.lock.json /opt/vllm-provenance/vllm.lock.json`
- 第 13 行：`COPY third_party/vllm-cu132-wheelhouse.lock.json /opt/vllm-provenance/wheelhouse.lock.json`
- 第 14 行：`COPY tools/verify_vllm_cu132_inputs.py /opt/vllm-provenance/verify_inputs.py`
- 第 15 行：`RUN python3 /opt/vllm-provenance/verify_inputs.py --source /opt/vllm-provenance/vllm-568afb3a13806beb53bb2e6bd518269357b237c0.tar.gz --source-lock /opt/vllm-provenance/vllm.lock.json --wheelhouse /wheelhouse-build --wheelhouse-lock /opt/vllm-provenance/wheelhouse.lock.json`
- 第 17 行：`COPY docker/requirements-cu132-build.txt /src/vllm/docker/requirements-cu132-build.txt`
- 第 18 行：`COPY docker/requirements-cu132-build.lock.txt /src/vllm/docker/requirements-cu132-build.lock.txt`
- 第 20 行：`FROM input-verify AS build`
- 第 21 行：`RUN patch -p1 < /tmp/vllm-cu132-torch.patch`
- 第 22 行：`RUN python3 -m pip install --break-system-packages --ignore-installed --no-index --require-hashes --find-links=/wheelhouse-build -r /src/vllm/docker/requirements-cu132-build.lock.txt`
- 第 23 行：`RUN python3 -m build --wheel --no-isolation --outdir /out`
- 第 25 行：`FROM scratch AS export`
- 第 26 行：`COPY --from=build /out/ /`

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

### `docker/Dockerfile.vllm-builder-cu132`

来源 SHA256：`bf613126d53bfe5325a6b2ed841bf0b0b8980fa553e389ed13485b4f7c9c7631`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。

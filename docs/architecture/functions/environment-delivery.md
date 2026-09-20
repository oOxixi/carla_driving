# 运行环境、启动入口与证据包维护

上级：[交付模块](../modules/support-delivery.md)；关联：[维护工具模块](../modules/support-tools.md)。

## 入口与环境不能分开看

正式车侧入口是 integration.carla_runner；root run/stop 包装器、docker entrypoints 和 scripts 是不同启动方式。它们决定 cwd、Python 环境、服务地址、模型配置、挂载路径和输出目录。某 Python 单元测试通过，不代表脚本会进入正确目录并加载同一依赖。

关键目录：[docker](../../../docker)、[scripts](../../../scripts)、[weights](../../../weights)、[config/repro](../../../config/repro)、[submission](../../../submission)。[support-tools](../modules/support-tools.md) 提供逐脚本参数索引。

## 产物分工

| 位置 | 用途 | 维护时注意 |
|---|---|---|
| artifacts | 运行生成的日志、截图、训练与临时结果 | 通常被 Git 忽略；路径存在不代表团队可复现 |
| metrics/reference_5070 | 固定机器/版本的参考证据 | 不能宣称是当前 J6P 实测 |
| challenge/dataset/releases | 版本化数据与发布清单 | 改内容必须产生可追溯新版本，不覆盖历史身份 |
| models / weights | 模型放置/下载约定 | 模型名称、revision、hash 与实际文件均要匹配 |
| submission | 发布材料和可复现说明 | 必须指向同一版本的代码/模型/配置/证据 |

## 具体已知入口风险

scripts/run_full_pipeline.sh 当前把 scripts 目录当 project_root，普通环境下随后 python -m 的模块查找会出错。该问题只记录；不能看到文件名“full_pipeline”就认定它是当前可靠主入口。
Qwen profile 默认与当前 Teacher cohort 可能不同，发布时要记录具体运行参数而不是只写“2B”。

## 后续维护依赖/镜像的核对路径

新增 Python 依赖先确认属于车控、ASR、Qwen、训练还是 HIL 环境，再核对相应 requirements 与镜像安装层、启动解释器、权重路径和 preflight。不要把仅训练依赖无差别放进车控运行镜像。

验证依次为构建/导入、CLI 参数解析、健康检查、最小请求、所需真实闭环；结果记录环境与版本。材料导出或文件哈希通过不能替代这些运行验证。本轮不构建镜像、不下载模型、不发布远端内容。

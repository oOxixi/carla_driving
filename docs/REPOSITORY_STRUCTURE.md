# 仓库目录说明

## 顶层目录

| 目录 | 内容 | 是否运行时生成 |
|---|---|---|
| `artifacts/` | 日志、截图、点云、临时报告、下载模型等本机输出；仅保留说明文件 | 是，不提交 |
| `car_control_A/` | 指令状态机、命令调度、看门狗和 A 组单元测试 | 否 |
| `car_control_B/` | Pure Pursuit/Stanley 横向控制、车道/路线跟踪和验证代码 | 否 |
| `car_control_C/` | 纵向速度、跟车、停车保持、TTC 等控制实现 | 否 |
| `car_control_D/` | 最终安全仲裁、执行反馈、约束检查和控制基准工具 | 否 |
| `CARLA-Language-Benchmark/` | 6192 条冻结语言 schema 回归数据、校验和与审计策略 | 否 |
| `CARLA_Language_Benchmark/` | 上述带连字符数据目录的 Python 可导入包装器 | 否 |
| `config/` | Docker/复现运行所用环境配置；正式模型配置均为 2B | 否 |
| `datasets/` | 小型可提交语言、多模态、代理集和复现清单 | 否 |
| `docker/` | 控制器、Qwen、CARLA 相关 Compose 与镜像构建文件 | 否 |
| `docs/` | 当前手册、复现文档、参考材料和保留报告 | 否 |
| `examples/` | 最小接口或离线调用示例 | 否 |
| `integration/` | CARLA 唯一正式入口、传感器桥、Qwen 异步边界、场景执行与证据生成 | 否 |
| `interfaces/` | 感知、模型请求、驾驶命令、计划、控制和反馈 JSON Schema | 否 |
| `metrics/` | 经说明、带原始来源和哈希的只读参考基准 | 否 |
| `models/` | 本地模型放置约定；大模型权重不提交 | 本地填充 |
| `notebooks/` | 只读复现和语音到 CARLA 的交互式说明 | 否 |
| `perception/` | 目标数据结构、投影/融合与感知基础组件 | 否 |
| `qwen_service/` | Qwen HTTP 客户端、兼容服务协议和服务级测试 | 否 |
| `runtime/` | 复杂度路由、计划校验/编译、编排和延迟跟踪 | 否 |
| `scenarios/` | 所有场景 JSON、schema、场景矩阵和场景内 README | 否 |
| `scripts/` | 人工/CI 使用的一键启动、正式场景运行和外部 ScenarioRunner 脚本 | 否 |
| `submission/` | 当前技术方案、证据模板和提交说明；不放临时跑测输出 | 否 |
| `third_party/` | 外部依赖的许可证、补丁或小型兼容材料 | 否 |
| `tools/` | 验证、审计、数据构建、基准测试和证据分析 CLI | 否 |
| `voice_group/` | ASR、语音解析、测试音频和语音组测试 | 否 |
| `weights/` | 固定版本模型权重下载脚本；实际权重不提交 | 本地填充 |

## 关键子目录

| 目录 | 内容 |
|---|---|
| `integration/tests/` | 主链、Qwen 边界、场景合同和故障回归测试 |
| `scenarios/official_competition/` | S1 5km、S2 8km、S3 6km 正式比赛场景 |
| `scenarios/qwen_routing/` | 简单快路径、复杂 Qwen 路径和歧义拒绝 |
| `scenarios/qwen_fullchain/` | Qwen 计划、编译、执行的全链合同 |
| `scenarios/qwen_faults/` | 超时、非法输出、断线和 D 抢占 |
| `scenarios/acceptance_suite/` | P0–P3 综合验收矩阵 |
| `docs/runbooks/` | 服务器运行和外部接入手册 |
| `docs/reproduction/` | Qwen 2B 固定版本、证据范围和复现步骤 |
| `metrics/reference_5070/` | 2B INT4 诊断基准、原始 JSON、日志和 SHA256 清单 |
| `submission/current/` | 当前技术方案源文件 |
| `submission/templates/` | 单次演示记录和机器可读证据索引模板 |

## 根目录文件

- `README.md`：项目总入口。
- `README_REPRO.md`：容器化独立复现入口。
- `requirements*.txt`：主程序、Qwen 客户端/服务/vLLM 的依赖分层。
- `run.sh`、`run.ps1`、`stop.sh`、`stop.ps1`：提交包跨平台容器入口。
- `compat.py`：A/C 控制模块共用的兼容层。
- `pytest.ini`：测试发现配置。

所有新增源码应进入明确职责包；新增运行证据进入 `artifacts/`；新文档进入 `docs/` 的
对应类别，避免再次创建日期命名的实现副本或根目录交接文件。

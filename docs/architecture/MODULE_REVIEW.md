# 20模块文档逐页复核记录

当前逐入口精读进度见[顺序精读记录](SEQUENTIAL_REVIEW.md)。前述全量静态复核不代表20模块已全部消除占位说明。

返回[总索引](README.md)。日期2026-09-20；代码基线fe1ba839；仅修改文档。机器结果见[module-audit.json](module-audit.json)。

## 范围与方法

遍历20个业务模块、3个聚合索引、26份语义功能页、358份逐文件记录及横向导航。491条源码/配置资源记录均存在，内容hash与原inventory一致；425份Python源码经AST读取，3635个函数/方法声明参与检查，旧清单中可对照的签名未发现漂移。源码不变只证明快照仍对应代码，不自动证明原文解释正确。

模块页已补各自输入输出、参数含义/覆盖、上下游和变更影响；核心实现的公开入口与类型/默认直接从源码登记。逐文件页补739处argparse声明、201个Schema节点（包括根/引用/分支，不等于201个独立业务字段）、1949处显式raise的局部条件。环境读取与数值校验、21个shell/PowerShell脚本参数摘录另见逐文件页。测试源码也在逐文件记录中，测试默认不能当成生产默认。

## 逐模块结果

| 模块 | 本轮补齐重点 | 验证界限 |
|---|---|---|
| [vehicle-entry](modules/vehicle-entry.md) | FrameResult、step参数、秒/纳秒、最终控制 | 未运行CARLA |
| [vehicle-planner](modules/vehicle-planner.md) | OrchestratorConfig、结果可空字段、V1/V2、超时分层 | 异步实际时序需run证据 |
| [vehicle-behavior](modules/vehicle-behavior.md) | A内部命令/请求/反馈、确认和生命周期 | 内部dataclass不等于JSON |
| [vehicle-lateral](modules/vehicle-lateral.md) | Pose/Route/Output、两种控制器参数、坐标单位 | 实际道路跟踪需闭环 |
| [vehicle-longitudinal](modules/vehicle-longitudinal.md) | 控制请求/输出、跟车公式、TTC缺失和参数范围 | 局部风险输出不代表全系统安全 |
| [vehicle-safety](modules/vehicle-safety.md) | SafetyConfig、policy覆盖、仲裁与反馈 | 锁存恢复需场景时序 |
| [vehicle-perception](modules/vehicle-perception.md) | PerceptionFrame/Sample、对象字段、时序与来源 | 传感器实际质量未测 |
| [vehicle-scenarios](modules/vehicle-scenarios.md) | 生成参数、验收合成、来源与数据资格 | A03/long证据缺口保留 |
| [vehicle-interfaces](modules/vehicle-interfaces.md) | Registry真实位置、7种Schema必填及详细约束 | Schema合法不证明可执行 |
| [challenge-structure](modules/challenge-structure.md) | 固定shape、model config、目标14维/状态64维槽位 | 未验证训练精度 |
| [challenge-planner](modules/challenge-planner.md) | Backend/Adapter签名、权重身份和ready条件 | Gate身份已知缺口保留 |
| [challenge-data](modules/challenge-data.md) | collector输入输出、release/view及拒绝资格 | Wave2原始运行证据未齐 |
| [challenge-training](modules/challenge-training.md) | 训练入口、两份配置逐键值、mask/候选交接 | 未启动训练或晋级 |
| [challenge-export](modules/challenge-export.md) | 随机结构导出、参数/metadata、X86边界 | 训练权重导出仍是能力缺口 |
| [challenge-hil](modules/challenge-hil.md) | Runtime协议、trace/能力、30s与1000ms区别 | 未做板端验收 |
| [support-voice](modules/support-voice.md) | 音频/文本入口、cascade及环境覆盖 | 未加载音频模型 |
| [support-qwen](modules/support-qwen.md) | 服务/HTTP/编排超时、token实值与图片限制 | 未请求真实服务 |
| [support-config-scenarios](modules/support-config-scenarios.md) | strategy/policy逐键值、派生min和override | 实际run配置需运行身份 |
| [support-delivery](modules/support-delivery.md) | 容器CMD/ENTRYPOINT、环境/路径与交付输入输出 | 未构建启动镜像 |
| [support-tools](modules/support-tools.md) | CLI完整声明、shell参数与转发、报告消费者 | 未运行会写产物的工具 |

## 纠正与补充的实际内容

- 原模块页存在重复的泛用依赖段，已改为各模块具体交接说明。
- 感知追踪器名称明确为SensorObjectTracker；接口注册器位于runtime/interface_registry.py。
- vLLM Planner的max_new_tokens签名默认256，但生效值强制1；image_max_side非224被拒绝。声明默认与生效值并列说明。
- D2 formal的max_updates=0表示不启用更新数上限，仍由epochs控制，不能解读为零次训练。
- controller镜像默认CMD为integration.demo_offline，不能当默认CARLA闭环入口。
- Student不再只有shape说明，补齐目标和状态每个槽位，明确63号状态槽未使用。

## 不能作出的保证

本轮可以确认导航、源码身份、声明和已核对的核心语义；不能声称每个运行分支均已实测。静态raise表不穷举被调函数异常；类型注解不自动证明运行值；hash一致不证明历史运行版本一致。文档中的缺口继续由AUDIT和Wave2记录追踪，没有通过写文档把业务问题标为修复。

## 顺序精读进度补充：第2模块

[异步规划](modules/vehicle-planner.md)已完成逐入口精读：21份实现页、189处占位改写、模块级具体参数索引及2份语义页边界补正；M02-01/M02-02为已复现未修复问题。此进度不代表20个模块全部精读完毕，后续顺序以[SEQUENTIAL_REVIEW](SEQUENTIAL_REVIEW.md)为准。

## 顺序精读进度补充：第3模块

[命令与状态机](modules/vehicle-behavior.md)逐项整理完成：10份实现页、137处占位改写，补齐具体参数、FSM状态、snapshot默认及实际消费边界。相关离线测试113 passed；M03-01–M03-03保留为未修复问题，实车影响未扩大推断。当前顺序精读完成3/20，详见[进度表](SEQUENTIAL_REVIEW.md)。

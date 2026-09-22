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

## 顺序精读进度补充：第4、5模块

[路线与横向控制](modules/vehicle-lateral.md)逐项整理完成：14份实现页、119处占位改写，补齐全局拓扑路线、场景局部路线、进度/恢复、坐标和生产 Pure Pursuit 有效参数；[专题页](modules/04_ROUTE_AND_LATERAL_CONTROL.md)纳入统一目录，RLC-01～RLC-05 保留为未关闭工程边界。[纵向控制](modules/vehicle-longitudinal.md)已完成13份实现页和83处占位改写，补齐生产链、速度约束、缺测、状态与重置边界，并登记M05-01配置生效缺口。当前顺序精读完成5/20，详见[进度表](SEQUENTIAL_REVIEW.md)。

## 顺序精读进度补充：第6模块

[感知](modules/vehicle-perception.md)已完成12份实现页复核和10页96处占位改写，区分runner生产bridge、C安全融合及独立perception benchmark管线，补齐帧同步、传感器门限、目标身份、canonical近似与来源审计；79项相关离线测试通过，M06-01/M06-02保留为未修复边界。当前顺序精读完成6/20。

## 顺序精读进度补充：第7模块

[安全仲裁](modules/vehicle-safety.md)已完成13份实现页复核和12页82处占位改写，区分生产实时链与 canonical D 封装，补齐输入收敛、覆盖优先级、动态阈值、命令终态、测量与计分证据边界；35项相关离线测试通过，M07-01保留为未修复的 canonical 控制/终态一致性边界。当前顺序精读完成7/20。

## 顺序精读进度补充：第8模块

[场景执行与评分](modules/vehicle-scenarios.md)已完成9份实现页复核和8页98处占位改写，区分场景合同/几何、主runner扩展、evidence/acceptance与外部固定 ScenarioRunner，补齐命令调度、actor坐标、泛化采样、事件时序、context和证据等级；134项相关离线测试通过，M08-01保留为外部 agent 的多模态/逐帧Qwen能力缺口。当前顺序精读完成8/20。

## 顺序精读进度补充：第9～11模块

[接口与坐标转换](modules/vehicle-interfaces.md)已核对7份Schema字段页、Registry、canonical bridge与版本语义，补齐验证层次、单位/坐标/ID/时钟和三类转换降级；43项离线测试通过，M09-01保留。[Student结构与预处理](modules/challenge-structure.md)完成5份实现页复核和23处占位改写，补齐四路张量、十Head、信息损失与mask，服务器23项测试通过并保留M10-01。[Student Planner](modules/challenge-planner.md)完成8份实现/语义页复核和22处占位改写，补齐双Backend、确定性修复、confirmation与权重就绪边界，服务器26项测试通过并保留M11-01。当前顺序精读完成11/20；以上均未修改业务代码，也不等于CARLA、正式权重或J6P验收。

## 顺序精读进度补充：第12～15模块

[Teacher数据治理](modules/challenge-data.md)完成33份实现页和301处占位改写，明确run/sample/release/view、身份/切分/排除证据；数据测试暴露M12-01外部冻结计划缺失。[蒸馏与晋级](modules/challenge-training.md)完成25份实现/配置页和103处占位改写，明确标签/mask/loss/checkpoint/纯权重/Gate，65项测试通过且A01保留。[导出与部署](modules/challenge-export.md)完成6份实现页和13处占位改写，artifact validator实际PASS，但R01/R03仍阻断真实权重到J6P闭环。[HIL与测量](modules/challenge-hil.md)完成20份实现/资源页和139处占位改写，71项测试通过且A02/A03/R02保留。当前顺序精读完成15/20；未训练正式Student或运行真实J6P。

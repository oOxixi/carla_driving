# B4 复现、版本台账与最终交付门禁

## 1. 模块目标

B4 负责从第一个候选开始维护唯一版本台账，把 A1/A2/A3/A4、B1/B2/B3 的模型、数据、代码、
配置、原始指标、Docker 和报告绑定成同一个可复现 Release Candidate，最后在干净环境中验证
并生成比赛提交包。

B4 只登记、核验和打包事实，不替其他成员补做实验，不修改 B2/B3 指标，不把缺失数据填成
0，不把开发候选、X86 预验证或随机模型包装成 Final，也不因为“文件齐了”绕过上游 Gate。

相关模块：

- [`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md)：模型与权重身份状态机。
- [`B2_EVALUATION_AND_FP32_GATE.md`](B2_EVALUATION_AND_FP32_GATE.md)：独立精度评价和 Frozen Test。
- [`A2_INT8_QUANTIZATION_AND_QAT.md`](A2_INT8_QUANTIZATION_AND_QAT.md)：INT8 产物身份与 Gate。
- [`A4_OPENEXPLORER_J6P_RUNTIME.md`](A4_OPENEXPLORER_J6P_RUNTIME.md)：J6P artifact 与 Runtime 交付。
- [`B3_HIL_J6P_INDEPENDENT_VALIDATION.md`](B3_HIL_J6P_INDEPENDENT_VALIDATION.md)：板端实测和原始证据。
- [`submission/README.md`](../../submission/README.md)：现有基础赛道提交材料入口。

## 2. 当前状态快照

核对日期：2026-09-21。代码基线：`challenge` 提交
`96cbd0da628a9a47d4e904c3e0eaf748aa0f9c50`。

| 能力/交付 | 当前状态 | 事实与限制 |
|---|---|---|
| 挑战赛道实验台账 | 未建立 | 没有 `EXPERIMENT_LEDGER.md` 或机器可读 ledger |
| Release Manifest 模板 | 未建立 | 没有挑战赛道 `RELEASE_MANIFEST_TEMPLATE.json` |
| 提交检查清单 | 未建立 | 没有挑战赛道 `submission_checklist.md` |
| `final_submission/` | 不存在 | 尚未到 Final Freeze 阶段 |
| Candidate 自动登记 | 未实现 | 没有 RC ID、Gate 状态机或唯一性检查入口 |
| 模型/代码哈希工具 | 部分可复用 | 有通用 SHA 工具，但未形成挑战赛道全包校验 |
| B3 运行清单 | 已实现 | 每个 HIL run 可生成文件级 `measurement_manifest.json` |
| 数据发布 manifest | 已实现多套 | B1 release 有内容哈希，但尚未绑定 Final candidate |
| Docker | 基础赛道可用 | 当前 Compose/镜像针对 CARLA 控制器和 Qwen 服务，不含 J6P Runtime |
| 提交包检查器 | 基础赛道专用 | `build_submission_package.py` 硬编码 Qwen 权重、RTX 5070 和基础材料 |
| 复现 CLI | 基础赛道专用 | `repro_cli.py` 运行 Qwen 全链，不是挑战赛道 Student/J6P 入口 |
| Source manifest | 部分可复用 | 只覆盖 Python，且包含未跟踪文件；不能单独代表 Final source |
| Model manifest | 部分可复用 | 只遍历模型目录顶层文件，不覆盖完整提交包 |
| 干净环境复现 | 未完成 | 没有另一成员对挑战赛道 Final 的独立复现记录 |
| Final 报告/视频 | 未交付 | 现有模板不能视为正式证据 |

当前仓库具备若干基础赛道打包工具和挑战赛道各模块 manifest，但尚没有把它们连接成 B4
发布链。B4 不能直接复用基础赛道 `check` 的 PASS 来证明挑战赛道提交完整。

## 3. Release Candidate 唯一身份

每个候选一经登记不可原地修改，至少包含：

```text
release_candidate_id
created_at_utc
git_sha
source_tree_status
model_id
model_sha256
dataset_version
dataset_manifest_sha256
config_id
fp32_weights_sha256
fp32_onnx_sha256
quantization_id
int8_artifact_sha256
compiled_model_sha256
runtime_id
runtime_manifest_sha256
docker_image_repository
docker_image_digest
b2_evaluation_id / result / manifest_sha256
b3_run_ids / result / measurement_manifest_sha256
known_issues
overall_status
```

RC ID 建议只引用不可变内容，例如 `rc-<date>-<git12>-<model12>`。显示名称可以变，RC ID、
artifact SHA 和历史 Gate 记录不得覆盖。任意模型、配置、代码、数据、Runtime 或 Docker 字节
变化都产生新候选。

## 4. 候选状态机

```text
DRAFT
  -> IDENTITY_VERIFIED
  -> B2_ACCURACY_PASSED
  -> A2_INT8_PASSED
  -> A4_RUNTIME_PASSED
  -> B3_HARDWARE_PASSED
  -> REPRODUCED_CLEAN
  -> FINAL
```

失败状态使用 `REJECTED_<GATE>`；缺输入使用 `BLOCKED_<INPUT>`；取不到指标使用
`NOT_MEASURED`。禁止把 `PENDING`、`NOT_MEASURED` 或 `X86_PRE_VALIDATED` 汇总成 PASS。

晋级记录必须写明 Gate、policy/schema 版本、证据相对路径和 SHA、执行者、时间、结论及失败
原因。布尔字段不能由 B4 手工改成 true；必须从签发方的机器可读证据导入并重新校验哈希。

## 5. 实验台账

台账既需要适合阅读的 `EXPERIMENT_LEDGER.md`，也需要机器可检查的 JSONL/JSON。每条记录至少
保存：

- experiment/run/RC ID、父候选和目的；
- branch、完整 Git SHA、工作区是否干净；
- 数据/视图/Benchmark、模型、配置和 Runtime 身份；
- 完整命令、环境/容器、随机种子和开始/结束时间；
- 输出目录、原始日志、summary 和每个 manifest SHA；
- 状态 `PASS/FAIL/INVALID/BLOCKED`；
- 结果摘要只能引用原始文件字段，不重复手填；
- 已知问题、负责人和后续动作。

台账追加写，不重写历史。作废记录保留并指向替代候选；删除失败实验会破坏模型演进和选择
依据，也无法证明没有挑选最好的一轮。

## 6. RELEASE_MANIFEST 结构

正式 `RELEASE_MANIFEST.json` 至少分为以下对象：

### 6.1 Release identity

`release_id`、RC ID、完整 Git SHA、tag、创建时间、状态、挑战赛道、schema 版本、负责人和
已知限制。

### 6.2 Source and interfaces

仓库 URL、commit、source tree manifest、Python/非 Python 配置清单、ModelRequest V1、
ManeuverPlan V2、Student 结构/Head schema 版本及 SHA。

### 6.3 Models

Teacher exact repo/revision/fingerprint；Student FP32 weights/ONNX；INT8 artifact/quant config；
compiled J6P model；每个条目记录相对路径、字节数、SHA256、格式、来源 manifest 和 Gate。

### 6.4 Data and benchmark

训练 release、派生视图、Calibration、B2 Frozen Test 和 Seen/Variant/Unseen manifest。Test
只登记身份和最终评价证据，不能复制进训练目录或暴露给训练代码。

### 6.5 Runtime and Docker

A4 runtime ID/command/manifest、OpenExplorer/SDK/BSP/固件、J6P artifact、Dockerfile SHA、
base image digest、build args、镜像 repo:tag、image ID/digest、离线 archive SHA 和启动命令。

### 6.6 Evidence and results

B2/B3 原始 run、policy、报告和 manifest 的相对路径/SHA。每个展示数字还要记录来源文件和
JSON key/CSV 计算口径，禁止只把表格数字抄进 manifest。

### 6.7 Reproduction and package

复现报告、操作者、干净环境、执行步骤、退出码、差异；提交文件清单、root digest、压缩包
文件名/字节数/SHA256、视频/报告可打开状态。

Manifest 自身不直接把自己的 SHA 写回自己。先生成全包文件清单（排除 manifest/root digest
文件），再生成 manifest，最后在包外生成 `SHA256SUMS` 或 archive SHA，避免自引用哈希。

## 7. Final Freeze 流程

### F0：停止功能变化

D7 后禁止模型结构重构、数据重新划分和指标口径变化，只允许阻断性 Bug、配置、复现和打包
修复。任何会改变模型行为的修复都退回对应 Gate 并产生新 RC。

### F1：冻结身份

确定并登记：

```text
FINAL_GIT_SHA
FINAL_MODEL_ID / FINAL_MODEL_SHA
FINAL_DATASET_VERSION / MANIFEST_SHA
FINAL_QUANT_CONFIG / INT8_SHA
FINAL_COMPILED_MODEL / SHA
FINAL_RUNTIME_ID / MANIFEST_SHA
FINAL_DOCKER_DIGEST
```

冻结时工作区必须干净，commit 可从远端重新获取。未提交文件、人工本地补丁和绝对路径不能
成为 Final 依赖。

### F2：重跑最终 Gate

- B2 使用 Final 身份重新跑 Frozen Test、official-like、Seen/Variant/Unseen；
- B3 对同一 J6P artifact/Runtime 再做至少 3 轮关键指标；
- B4 校验报告里的每个模型 SHA、Git SHA 与 Final 一致；
- 旧 RC 报告不能通过改文件名进入 Final。

### F3：构建和暂存

从干净 checkout 构建 Docker 与 `final_submission/`，不得从开发工作区随手复制。暂存目录只
允许 manifest 白名单文件；生成后只读，不再原地编辑。

### F4：独立复现

由没有参与该构建的成员在新的目录/机器执行 clone、校验、安装/加载 Docker、加载模型、固定
样例和 Benchmark 关键入口。完整记录命令、stdout/stderr、退出码、环境和新生成结果 SHA。

### F5：封包与终检

验证相对路径、大小写、Unicode、权限、可执行位、软链接、空文件、秘密信息、archive 解压、
报告可打开、视频可播放和所有 SHA。压缩包生成后再计算外部 SHA256，并在独立目录解压复验。

## 8. Docker 交付合同

挑战赛道最终 Docker 必须加载 Final Student/J6P Runtime，而不是仓库现有 Qwen 基础赛道默认
入口。至少记录：

- Dockerfile、compose/启动脚本和所有 lockfile SHA；
- base image 的 immutable digest，不只记录浮动 tag；
- OpenExplorer/J6P Runtime 许可允许的分发方式；
- build command、build args、目标架构和 BuildKit/engine 版本；
- image ID、repo digest、archive SHA 和大小；
- 模型是镜像内、只读挂载还是板端外部存储；
- 容器内 `--describe` 输出与 RELEASE_MANIFEST 一致；
- healthcheck、固定样例、日志/输出目录和无网运行要求；
- GPU/BPU/设备节点、driver/BSP 等宿主机前置条件。

当前 `docker/compose.yaml`、`Dockerfile.controller` 和 Qwen Dockerfile 可作为工程参考，但没有
包含挑战赛道 J6P Student Runtime。`verify-stack.ps1` PASS 只证明当前 Compose 可解析/构建，
不能视为挑战赛道 Docker Gate。

## 9. 干净环境复现合同

复现必须从空目录和远端 commit 开始，不复用开发者的虚拟环境、模型缓存或未登记 volume：

```text
clone/fetch exact commit
-> verify source and release manifest
-> verify/download content-addressed artifacts
-> build or load exact Docker digest
-> runtime --describe
-> fixed request smoke
-> B2 key evaluation entry
-> B3 contract / key replay entry
-> compare identities and bounded outputs
-> write reproduction_report + evidence manifest
```

复现结果不要求延迟逐毫秒相同，但身份、schema、固定输入的结构化输出、Gate 状态和统计口径
必须一致。性能差异要结合硬件/环境指纹解释，不能静默替换原始 Final 指标。

`reproduction_report` 至少包含环境、操作者、开始/结束、网络条件、命令、exit code、每步
PASS/FAIL、生成文件 SHA、与 Release 的差异和最终结论。任何人工干预都要记录。

## 10. 最终提交目录

```text
final_submission/
├── README.md
├── REPRODUCTION.md
├── RELEASE_MANIFEST.json
├── SHA256SUMS
├── model/
│   ├── student_fp32.*
│   ├── student_int8.*
│   ├── compiled_j6p.*
│   └── manifests/
├── code/
├── configs/
├── docker/
│   ├── Dockerfile
│   ├── compose.yaml
│   ├── image_info.md
│   └── lockfiles/
├── reports/
│   ├── lightweight_strategy_report.*
│   ├── model_comparison.*
│   ├── j6p_test_report.*
│   └── reproduction_report.*
├── raw_metrics/
│   ├── accuracy/
│   ├── latency/
│   ├── memory/
│   ├── power/
│   └── utilization/
└── demo/
```

训练缓存、下载缓存、临时 checkpoint、失败候选的大型权重、`__pycache__`、`.pytest_cache`、
本机日志、秘密/令牌、绝对路径和重复数据集不得进入 Final。中间模型与失败记录保留在团队
artifact storage/台账中；比赛明确要求时才按白名单放入 `intermediate_models/`。

## 11. 报告和数字追溯

每个最终结论必须同时给出：值、单位、对象、设备、样本/轮数、policy、原始文件、字段/计算
公式和 manifest SHA。例如 J6P P95 不能只写 `120 ms`，还需绑定 Final compiled model、
Runtime、B3 run、`latency_raw.csv`、READY 样本数和分位数算法。

报告生成器可以读取原始结果渲染表格，但不得把报告反向当原始真值。手工修改报告数字后
hash 会失配，必须阻断发布。`NOT_RUN`、`NOT_MEASURED` 和失败结果要如实保留。

## 12. 演示与视频证据

演示脚本绑定 Final RC、固定场景/seed/route 和成功判据。视频至少能对应 run ID、画面时间、
指令/计划、关键事件、最终状态和原始日志；剪辑不能隐藏失败后重跑，也不能用另一个模型的
画面配 Final 报告。

演示视频是展示证据，不替代原始指标。视频文件记录时长、编码、分辨率、字节数和 SHA256，
并在 `DEMO_RECORD.md` 中写明对应 run 与结论范围。

## 13. 可复用工具与适用边界

| 现有工具 | 可复用内容 | 不能证明 |
|---|---|---|
| `generate_model_manifest.py` | 顶层模型文件 SHA/大小 | 递归全包、Gate 或 J6P 可运行 |
| `verify_model_manifest.py` | 模型文件集合、路径安全和 SHA | 挑战赛道完整 Release |
| `verify_release_lock.py` | 单个锁定 artifact | 多资产一致性和 Final Gate |
| `generate_source_manifest.py` | Python 文件清单 | 非 Python 配置；且清洁前会包含 untracked Python |
| `build_submission_package.py check` | 基础赛道外部材料缺失检查 | Student/J6P 提交完整性 |
| `repro_cli.py` | 基础赛道 Qwen 复现流程参考 | 挑战赛道 Student 复现 |
| `docker/scripts/*` | Compose 校验、镜像导出与 archive SHA | J6P Runtime 已装入镜像 |
| B3 `measurement_manifest.json` | 单次测量目录完整性 | 整个 Final 包完整性 |

正式 B4 工程应复用底层哈希函数和安全路径规则，但另建挑战赛道 schema/validator，而不是在
基础赛道脚本中混入条件分支后继续使用同一个“PASS”含义。

## 14. 待实现的机器门禁

当前没有挑战赛道 B4 CLI。后续入口至少应支持：

1. 初始化/追加 Candidate ledger；
2. 从 A/B 各组 manifest 导入 RC，拒绝哈希漂移和重复 ID；
3. 校验 Gate 状态机和所有证据路径；
4. 构建白名单暂存目录并生成文件级 SHA；
5. 检查绝对路径、软链接、空文件、未跟踪依赖、秘密和临时文件；
6. 验证 Docker digest、容器内模型身份和固定样例；
7. 生成/校验 RELEASE_MANIFEST；
8. 导入独立 reproduction report；
9. 生成 archive、外部 SHA 和最终 checklist。

入口名称和命令在实现前保持未定义，本文不虚构一个不存在的 `challenge.release` 命令。

## 15. G5 Release 门禁

| 检查 | PASS 条件 |
|---|---|
| Final identity | 代码、数据、FP32、INT8、J6P、Runtime、Docker 全部唯一且一致 |
| 上游 Gate | B2 精度、A2 INT8、A4 Runtime、B3 J6P 都绑定同一 RC 并 PASS |
| Benchmark | 使用 B2 签发 Frozen Test，无训练泄漏 |
| Raw evidence | 报告全部可追溯到 B2/B3 原始结果和 SHA |
| Docker | 容器实际加载 Final artifact，固定样例可运行 |
| Reproduction | 另一成员在干净环境完成关键流程并签发报告 |
| Package | 目录白名单、路径、文件、权限、SHA、解压复验全部通过 |
| Claims | 不把 X86 写成 J6P，不把估算写成实测，不隐藏 NOT_MEASURED |
| Human artifacts | README/PDF/视频可打开，内容与 Final RC 一致 |

任一关键项失败时整体不是 Final。B4 可以发布阻塞清单，但不能为了截止时间把状态改成 PASS。

## 16. 当前阻塞与完成定义

| 阻塞 | 关闭条件 |
|---|---|
| 无 B4 台账/schema/checklist | 建立版本化模板、机器校验和测试 |
| 无正式 RC | 上游产生身份完整且经过 Gate 的候选 |
| 基础/挑战打包逻辑混杂 | 为 Student/J6P 建独立 Release schema 和 validator |
| Source manifest 不完整 | 覆盖全部运行代码/配置并拒绝脏工作区和未跟踪依赖 |
| Docker 不含挑战 Runtime | A4/B4 构建固定 digest 的 Student/J6P 交付镜像/运行包 |
| 无 Final Benchmark/J6P 证据 | B2/B3 对同一 RC 签发最终证据 |
| 无干净环境复现 | 独立成员从 exact commit 完成关键流程并生成 manifest |
| 无 Final package | 从白名单暂存、校验、封包并解压复验 |
| 无正式报告/演示 | 所有材料绑定 Final RC 和原始证据 |

模块完成的标准是：任意接收者拿到提交 archive 和外部 SHA 后，能验证目录未被篡改，从
RELEASE_MANIFEST 找到唯一代码、数据、模型、配置、Runtime 和 Docker 身份，在干净环境按
REPRODUCTION 跑通固定样例和关键评价入口，并把 README、报告和视频里的每个数字追溯到
B2/B3 原始证据；不存在临时文件、失效路径、旧候选、基础赛道 Qwen 结果冒充挑战赛道结果
或无法解释的人工改动。当前仓库尚未达到该状态。

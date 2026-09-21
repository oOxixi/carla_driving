# B3 HIL、J6P 独立实测与证据门禁

## 1. 模块目标

B3 负责使用 A4 交付的**同一个** Runtime，在冻结回放、CARLA 闭环和 J6P 实机环境中独立
测量正确性、延迟、内存、功耗、CPU/BPU 利用率、异常恢复与长时间稳定性，并把原始证据
交给 B2/B4 汇总。

B3 不训练或量化 Student，不修改 A4 主部署实现，不创建第二套“测试专用 Runtime”，不拥有
Seen/Variant/Unseen 的定义权，也不能为了得到更好数字改变模型、输入、控制链或 Gate。

相关模块：

- [`B2_EVALUATION_AND_FP32_GATE.md`](B2_EVALUATION_AND_FP32_GATE.md)：冻结 Benchmark 与最终精度判定。
- [`A4_OPENEXPLORER_J6P_RUNTIME.md`](A4_OPENEXPLORER_J6P_RUNTIME.md)：被测 Runtime 和 J6P 交付合同。
- [`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md)：模型、权重和 Runtime 身份链。
- [`challenge/hil/README.md`](../../challenge/hil/README.md)：当前 HIL 工具和可执行命令入口。
- [`challenge/hil/a4_runtime_contract.md`](../../challenge/hil/a4_runtime_contract.md)：A4 Runtime 可测性合同。
- [`B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md`](B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md)：B3 原始证据进入 Final 的绑定与复现门禁。

## 2. 当前状态快照

核对日期：2026-09-21。代码基线：`challenge` 提交
`27cceafeb66365223c5abf8a22ee648ac253e3fa`。

| 能力 | 当前状态 | 事实与限制 |
|---|---|---|
| HIL 回放框架 | 已实现 | 支持进程内、ONNX 和板端 CLI adapter |
| 八阶段计时 | 已实现 | T0～T7、单调性、分位数和原始纳秒时间戳 |
| 原始指标文件 | 已实现 | latency/memory/power/utilization CSV 与 manifest |
| 环境指纹 | 已实现 | 电源、负载、CPU 标定、库版本、时钟和 artifact 身份 |
| 多轮运行 | 已实现 | 默认 3 轮、warmup 与 measured 分离 |
| 异常输入与 Hard-case 交接 | 已实现 | 健壮性向量与可训练语义失败分离 |
| 长稳入口 | 已实现 | 默认 30 分钟，带内存漂移和 recovery probe |
| 开发回放快照 | 已冻结 | D2 v1.1 Val 539 例、539 张 RGB、内容寻址 |
| X86 策展证据 | 已完成机制预验证 | 随机初始化模型，只证明工具链，不证明精度/性能达标 |
| 真实 A3/A2/A4 candidate | 未交付 | 当前没有可用于正式结论的完整 Runtime 身份链 |
| B2 Frozen Benchmark | 未交付 | D2 Val 和 reserved candidates 都不是正式 Frozen Test |
| A4 生产 Runtime | 未交付 | 当前 X86 脚本不符合请求→计划和打点合同 |
| J6P 实机与遥测 | 未接入 | 无板端产物、板卡、功耗探针和 BPU 数据 |
| Seen/Variant/Unseen 正式结果 | 未完成 | 缺 B2 case manifest 和真实 Student Runtime |

当前证据目录中的 X86 数字来自随机初始化 FP32 结构，功耗/BPU 为 `NOT_APPLICABLE`，长稳
只有 15 秒机制 Smoke。它们不能晋级为正式候选基线，也不能与最终 J6P Gate 混用。

## 3. 证据层级与结论权限

| 级别 | 被测对象与环境 | 允许结论 |
|---|---|---|
| E0 工具自测 | synthetic trace / fake runtime | 统计、schema、错误处理机制可运行 |
| E1 结构预验证 | 随机 Student、开发 Val、X86 | 工具链与接口路径可运行 |
| E2 Candidate X86 | Gate-passed candidate、A4 同入口、X86 | 同机相对趋势和预验证 |
| E3 J6P Bring-up | 编译产物、J6P、冻结真实输入 | 模型加载与功能一致性 |
| E4 J6P Independent Measured | 正式 Runtime、实机遥测、≥3 轮 | 可报告真实板端指标 |
| E5 Final Gate Evidence | Final 身份、Frozen Test、闭环与复现包 | 可交 B2/B4 签发最终结论 |

结论权限由证据决定，不由目录名或命令参数决定。仅填写
`--device-class J6P_BOARD` 不能把 X86 运行变成板端证据；必须同时核验 artifact、硬件环境、
Runtime 身份、板端日志和探针来源。

## 4. 正式测量前置输入

### 4.1 A3/A2/A4 被测候选

B3 正式运行必须收到：

- A3 Gate-passed FP32 权重和 manifest；
- A2 Gate-passed INT8 candidate、quant config 与 source 身份链；
- A4 compiled J6P artifact、实际加载 artifact SHA256 和 Runtime manifest；
- A4 启动命令、常驻模式、`--describe`、trace、model-only 和契约自检报告；
- OpenExplorer/SDK/BSP/固件、CPU/BPU fallback 与已知限制；
- 所有代码和配置的固定 Git SHA/内容哈希。

B3 现场重算实际加载文件的 SHA256，不只相信 manifest 自述。任一身份不一致即停止测试，
不得测完再在报告中补注“可能不是同一模型”。

### 4.2 B2 Benchmark 输入

B2 提供不向 A 组泄露的冻结 case manifest、Seen/Variant/Unseen 标签、场景/seed/route、成功
判据和异构利用率正式公式。B3 只执行，不调整分组和阈值。

`challenge/hil/frozen/d2_v1_1_val` 是可复现的开发回放快照，可用于契约、调试和性能采样，
不能作为 B2 Frozen Test。`reserved_test_candidates` 也只有经过 B2 治理和重新签发后才能
成为正式评价输入。

### 4.3 硬件与遥测

正式 J6P 测量要固定板卡型号、BSP/SDK/固件、散热、电源模式、CPU governor、BPU 频率、
是否独占设备，以及功耗/BPU 探针命令、采样率和取电点。取不到的量写 `NOT_APPLICABLE`
或 `NOT_MEASURED`，禁止用 TDP、文件大小或工具估算值填空。

## 5. 输入冻结与运行身份

每次正式 run 绑定：

```text
run_id
git_sha
model_id
model_sha256
dataset_version
config_id
runtime_id / runtime_manifest_sha256
benchmark_manifest_sha256
scenario + seed + route_hash
hardware_env fingerprint
```

冻结快照至少包含完整 ModelRequest、内容寻址 RGB、Teacher plan、case/group ID、split 标签、
文件 SHA256 和集合 digest。run 开始后输入、顺序、warmup、轮数、采样频率和超时预算不得
变化；变化即创建新 run，不覆盖旧结果。

## 6. 运行前四级预检

### P0：证据与环境

- 工作区、Runtime、artifact、Benchmark 和配置哈希一致；
- `hardware_env.json` 可完整生成；
- 板端无无关负载，电源/温度/频率状态可记录；
- 原始输出目录为空或使用新的 run ID。

### P1：产物结构

用 `artifact` 检查 opset、固定输入 Shape、输出名称/顺序、禁用动态/控制流算子和 SHA。
这一步只证明结构，不证明精度或板端可执行。

### P2：Runtime 合同

用 `contract` 验证 stdin ModelRequest→stdout ManeuverPlan、ID 回显、计划结构、禁用低层控制
输出、阶段打点和延迟预算。合同失败时先退回 A4，B3 不在 adapter 里补一套生产逻辑。

当前 `BoardCliRuntime` 每个请求启动一次子进程，并没有驱动独立 `--describe`、常驻/批量或
`--model-only --input` 子命令；因此现有 `contract` 只能验证其已覆盖部分。正式验收前需要
补齐这些检查，否则不能声称完整 A4 Runtime 合同 PASS。

### P3：输出一致性

使用同一冻结输入比较 reference 与 candidate 的十个 raw Head、计划结构和生产入口输出。
容差与精度判定来自 A2/B2；B3 不根据结果临时扩大容差。

## 7. Seen、Variant、Unseen 测试矩阵

正式最小矩阵包含 S1/S2/S3、至少一个固定 Variant 和一个固定 Unseen。每个 case 的 Teacher
与 Student 使用完全相同的 scenario、seed、route、环境和初始状态：

```text
Teacher: scenario=X, seed=Y, route=Z
Student: scenario=X, seed=Y, route=Z
```

每次保存 ModelRequest、Teacher Plan、Student Plan、原始 Head（若接口允许）、A/B/C/D 执行
结果、时间戳、安全接管、失败分类和闭环 summary。基础控制链故障必须单独归因，不能自动
记为模型失败，也不能通过修改 A/B/C/D 迁就 Student。

Variant/Unseen 的目标是检查泛化，不是增加场景数量。禁止按 scenario ID、地图坐标、seed、
路线或评测标签走特判。

## 8. 延迟测量口径

固定八个单调纳秒计时点：

```text
input_arrival -> preprocess_end -> packing_end -> inference_start
-> inference_end -> postprocess_end -> adapter_end -> plan_ready
```

必须同时报告：

- `model_only_ms = inference_end - inference_start`；
- `planner_e2e_ms = plan_ready - input_arrival`；
- 预处理、packing、提交/搬运、后处理、Adapter 和 Validator；
- `planner_overhead_ms = planner_e2e_ms - model_only_ms`；
- 每段 count/mean/P50/P95/P99/max、READY/ERROR/TIMEOUT/REJECTED 数量。

warmup 样本写入原始 CSV 但不进入正式统计；模型加载单列。失败/超时不混入 READY 分位数，
必须同时报告失败率。当前线性插值分位数已与仓库基础链口径对齐。

## 9. 内存、功耗与异构利用率

### 9.1 内存

记录 planner 进程 RSS、peak RSS；如有板端 Runtime workspace 或整机 DDR，使用不同 scope
分别记录。不得用模型文件大小代替运行内存。

### 9.2 功耗

记录测量窗口、取电点、scope、探针来源、采样率、电压、电流、瞬时功率、时间加权平均值和
峰值。idle baseline 可额外报告，但不能用“负载功耗减 idle”替换官方整板口径。

### 9.3 CPU/BPU 与异构利用率

保存 CPU 与 BPU 原始采样、BPU 是否独占、可用/忙周期或厂商工具定义、DDR 带宽和采样
窗口。当前正式异构公式仍待 A4/B2 确认；确认前只允许报告原始采样，不允许给出“异构利用率
= xx%”的 Gate 结论。

## 10. 多轮、长稳与恢复

- 同一配置至少 3 轮，分别保存单轮和合并统计；
- 正式长稳默认 30 分钟，覆盖稳定负载和温度进入稳态后的窗口；
- 记录请求成功率、延迟趋势、RSS 漂移、功耗、BPU、温度和 throttling；
- 长稳结束立即执行 recovery probe，确认 Runtime 仍能输出合法计划；
- 崩溃、hang、模型重载、内存持续增长或热降频都进入原始日志和失败分类；
- 不只保留最快一轮，不因慢轮“环境不好”而删除；无效轮必须按事先规则标记并保留。

长稳中的探针采样会扰动绝对延迟，因此它用于趋势/恢复，正式延迟 Gate 仍以独立
`latency_raw.csv` 为准。

## 11. 异常、失败归因与 A3 回流

异常套件至少覆盖缺字段、缺图、NaN/Inf、超长 targets/text、deadline、硬停约束、Runtime
超时与非法输出。目标是验证 fail closed、有界响应和可恢复，不是要求所有坏输入都产出计划。

B3 向 A3 交接时严格分开：

- 真实语义失败：有 Teacher 标注、非 Frozen Test，才可标 `usable_for_training=true`；
- 合成健壮性向量：只用于验证，永远不能训练；
- Frozen Test 失败：只进入独立评价，不能回流训练；
- Runtime/部署失败：退回 A4，不伪装成模型 Hard case；
- 基础链失败：交对应 main 控制模块，不归咎 Student。

补训或 Runtime 修复后产生新 artifact SHA，必须完整重跑相应 Gate，不能沿用旧报告。

## 12. 正式门禁矩阵

| Gate | PASS 条件 | 失败归属 |
|---|---|---|
| Runtime 合同 | 请求/计划、身份、trace、常驻、model-only 全部可测 | A4 |
| 产物一致性 | 实际 artifact 身份正确，raw Head/计划无未解释漂移 | A2/A4 |
| 闭环结构 | Seen 无结构性失败，Variant/Unseen 无模板化错误 | A3/基础链分开归因 |
| 延迟 | E2E ≤200 ms；内部 J6P P95 目标 ≤150 ms | A4 |
| 内存 | 运行内存 ≤512 MB；内部目标 ≤450 MB | A4 |
| 功耗 | 平均功耗 ≤25 W，真实探针 | A4/B3 测量 |
| 异构利用率 | ≥80%，使用 B2 固定公式 | A4/B2 |
| 精度 | 最终相对 Teacher 累计核心衰减 ≤3% | B2 |
| 稳定性 | ≥30 分钟、无结构性失败、漂移受控、恢复成功 | A4/B3 |
| 可追溯性 | 原始日志、五标识、环境和 SHA 清单齐全 | B3/B4 |

B3 输出原始事实和独立测量结论；B2 负责统一精度/版本比较和最终 PASS/FAIL。若某项无法测，
状态是 `NOT_MEASURED`，不是默认 PASS。

## 13. 正式运行产物

每个 run 建议保持现有布局：

```text
<run_id>/
├── hardware_env.json
├── measurement_manifest.json
├── contract_report.json
├── artifact_report.json
├── consistency_report.json
├── hil_replay.jsonl
├── hil_replay_plans.jsonl
├── hil_replay_summary.json
├── latency_raw.csv
├── latency_summary.json
├── memory_raw.csv
├── power_raw.csv
├── utilization_raw.csv
├── stability_logs/
├── failure_cases/
├── handoff/
└── j6p_test_report.md
```

`measurement_manifest.json` 登记除自身外每个文件的相对路径、大小和 SHA256。最终包还要由
B4 将 Runtime manifest、Benchmark manifest 和 run manifest 互相绑定，防止模型、报告和
Docker 指向不同候选。

## 14. 当前可执行流程

工具自检和 schema：

```bash
python -m challenge.hil.cli selftest
python -m pytest -q challenge/hil/tests
python -m challenge.hil.cli schema --out artifacts/b3/schema
```

当前 D2 开发 Val 的 X86 机制回放：

```bash
python -m challenge.hil.cli run \
  --repo . \
  --adapter both \
  --onnx challenge/student_v0_fp32.onnx \
  --frozen challenge/hil/frozen/d2_v1_1_val \
  --rounds 3 --warmup 5 --limit 100 \
  --verify-consistency --verify-backend-consistency \
  --out artifacts/b3/x86_prevalidation
```

拿到 A4 正式入口后的板端模板：

```bash
python -m challenge.hil.cli contract \
  --repo . \
  --adapter board \
  --board-command "<A4 runtime command> --trace" \
  --board-artifact <compiled-j6p-artifact> \
  --frozen <B2-signed-snapshot> \
  --device-class J6P_BOARD \
  --out artifacts/b3/contract

python -m challenge.hil.cli run \
  --repo . \
  --adapter board \
  --board-command "<A4 runtime command> --trace" \
  --board-artifact <compiled-j6p-artifact> \
  --frozen <B2-signed-snapshot> \
  --rounds 3 --warmup 5 \
  --device-class J6P_BOARD \
  --accelerator-kind bpu \
  --power-probe-command "<power probe>" \
  --utilization-probe-command "<utilization probe>" \
  --out artifacts/b3/j6p_runs
```

这些模板只有在占位符替换为固定、可审计的真实值后才可用于正式测量。

## 15. 现有证据应如何解读

`challenge/hil/evidence/x86_prevalidation_20260918` 已证明：schema、八阶段打点、三轮调度、
torch↔ONNX 原始输出比较、生产入口一致性、异常归档和内容哈希清单能够协同工作。其输入是
D2 Val 前 100 例 ×3 轮，另有 15 秒 soak。

但它具有四个硬限制：随机初始化权重、B3 自建 adapter 而非 A4 Runtime、无 J6P/功耗/BPU、
开发 Val 而非 Frozen Test。因此其中延迟只能作为工具链演练记录，不能进入最终计分表。

此外，当前 `hil_replay_summary.json` 生成逻辑会固定写“Student weights are not A3-gated”，
即使未来传入正式权重也不会自动晋级其 Teacher comparison 结论。正式候选测试前应让该结论
由已核验的 weights/runtime manifest 决定，并增加回归测试，避免真实 Gate 结果仍被错误标成
诊断用途，或反向被人工修改成正式结论。

## 16. 当前阻塞与完成定义

| 阻塞 | 关闭条件 |
|---|---|
| 无真实 Final candidate | A3/A2/A4 提供贯通 manifest 的 FP32、INT8、J6P Runtime |
| 无 B2 Frozen Benchmark | B2 签发 Seen/Variant/Unseen manifest、判据和防泄露流程 |
| A4 Runtime 合同不完整 | 请求入口、describe、常驻、trace、model-only 全部实现并自检 |
| Board adapter 覆盖不完整 | B3 能独立检查 describe、常驻/批量和 model-only 路径 |
| 回放结论固定为 DIAGNOSTIC_ONLY | 根据已核验 Gate 身份自动生成可信范围并测试 fail closed |
| 无 J6P/遥测 | 接入真实板卡、功耗取电点、BPU 工具和环境记录 |
| 异构公式未冻结 | B2/A4 签发分子、分母、采样窗口和共享规则 |
| 无正式闭环矩阵 | 同条件运行 S1/S2/S3、Variant、Unseen 并正确归因 |
| 无正式长稳 | Final Runtime 完成 ≥30 分钟和 recovery probe |
| 无独立最终结论 | B2/B3/B4 对同一 artifact 和证据清单完成 Gate/复现 |

模块完成的标准是：B3 在不修改被测对象的情况下，能从 B2 签发的冻结输入驱动 A4 的同一
生产 Runtime，在 J6P 上完成至少三轮 Seen/Variant/Unseen、异常和 30 分钟长稳；模型纯推理、
Planner E2E、内存、功耗和 CPU/BPU 都有真实原始数据；每个数字可回溯到同一模型、Runtime、
Benchmark、硬件环境和文件 SHA；B2/B4 能从清单独立复算并确认 Final 包没有混入 X86、随机
模型或旧候选证据。当前仓库尚未达到该状态。

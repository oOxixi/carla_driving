# A4 OpenExplorer、X86/J6P Runtime 与性能优化门禁

## 1. 模块目标

A4 负责把 A2 签发的、已通过精度门禁的固定 Shape INT8 Student 转换成 J6P 可加载产物，
实现与主链合同一致的 Runtime，并在不改变 Planner 语义的前提下优化预处理、数据搬运、
推理和后处理。A4 同时提供足够的身份、打点和遥测接口，使 B3 能对同一个 Runtime 做独立
复测。

A4 不训练 Student、不决定 INT8 精度是否通过、不修改 ModelRequest/ManeuverPlan、A/B/C/D
或 SafetySupervisor，也不签发最终性能结论。OpenExplorer 编译成功、X86 可运行和 J6P
实机达标是三个不同证据等级。

相关模块：

- [`A2_INT8_QUANTIZATION_AND_QAT.md`](A2_INT8_QUANTIZATION_AND_QAT.md)：A4 的正式输入和 INT8 Gate。
- [`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md)：FP32、INT8 与 Runtime 的身份链。
- [`challenge/A1_MODEL_INTERFACE.md`](../../challenge/A1_MODEL_INTERFACE.md)：固定四输入、十输出合同。
- [`challenge/hil/a4_runtime_contract.md`](../../challenge/hil/a4_runtime_contract.md)：B3 可执行 Runtime 接口合同。
- [`challenge/hil/README.md`](../../challenge/hil/README.md)：B3 独立测量工具、口径和当前阻塞。
- [`B3_HIL_J6P_INDEPENDENT_VALIDATION.md`](B3_HIL_J6P_INDEPENDENT_VALIDATION.md)：A4 交付后的独立实测和最终证据门禁。

## 2. 当前状态快照

核对日期：2026-09-21。代码基线：`challenge` 提交
`32ed1325fb4d487c165110a01236dbdbe539f943`。

| 能力 | 当前状态 | 代码事实 |
|---|---|---|
| 固定 Shape FP32 ONNX | 结构冒烟已完成 | `challenge/student_v0_fp32.onnx` 是随机初始化产物 |
| X86 模型级计时 | 已有 Smoke | `student_x86.py` 用全零张量和 CPUExecutionProvider 跑前向 |
| X86 请求到计划全链 | 未实现 | 现有脚本不读 ModelRequest，也不输出 ManeuverPlan |
| Runtime 身份查询 | 未实现 | 没有 `--describe`，性能档案没有 artifact SHA 或五标识 |
| Runtime 分阶段打点 | 未实现 | 没有 T0～T7 单调纳秒时间戳 |
| 常驻/批量模式 | 未实现 | `x86_run.sh` 每次启动新进程 |
| OpenExplorer 环境 | 未冻结 | 没有版本、容器 digest、转换配置或可复现命令 |
| 算子兼容性 | 仅列清单 | `operator_mapping.md` 的 OpenExplorer/J6P 状态均待验证 |
| INT8 输入产物 | 未交付 | 仓库没有 Gate-passed Student INT8 artifact |
| J6P 编译产物 | 未交付 | 没有 `.bin`、编译日志、fallback 报告或 SHA256 |
| J6P Runtime | 未实现 | 没有 `j6p_run.sh` 或板端生产入口 |
| 板端功耗/BPU 遥测 | 未接入 | B3 schema/采样合同已就绪，真实探针缺失 |
| B3 契约检查 | 工具已就绪 | `challenge.hil.cli contract` 可检查入口、计划和打点 |

当前 `runtime_profile_x86.json` 的延迟只对应一次未记录完整环境的 X86 CPU Smoke，且输入
为全零张量。它不能证明真实请求全链、INT8、OpenExplorer、J6P、功耗、内存或异构利用率
达标。

## 3. 正确的部署顺序

```text
A2 INT8 Gate PASS candidate
  -> 核验 source FP32 / INT8 / calibration / quant config 身份
  -> 锁定 OpenExplorer、SDK、BSP、固件和容器
  -> 固定 Shape、输入 dtype、预处理与十输出合同检查
  -> 算子支持与 CPU fallback 预检查
  -> OpenExplorer 编译并签发 compiled artifact manifest
  -> X86/模拟器功能预验证
  -> J6P Runtime 请求到计划全链验证
  -> A4 Runtime 合同自检
  -> 正确性、长稳和恢复门禁
  -> 性能剖析与通用优化
  -> B3 在同一产物、同一入口上独立实测
  -> B2 汇总最终精度与挑战赛道结果
```

随机初始化 ONNX 可用于提前打通命令和文件格式，但必须标记 `SMOKE_ONLY`。不能把它编译
后的数字写成正式性能结果，也不能在真实 INT8 到来后沿用旧 artifact 的身份或报告。

## 4. 上游输入合同

A4 正式转换只接受 A2 的完整交接包：

- `gate_status=A2_INT8_GATE_PASSED` 或团队固定的等价状态；
- INT8 ONNX/中间产物及其 SHA256、`quantization_id` 和 manifest；
- source FP32 weights、FP32 ONNX 与 Gate manifest 的身份链；
- `model_id/config_id/dataset_version/git_sha`；
- calibration release、quant config、工具版本和敏感层/混合精度说明；
- batch=1 的四输入名称、Shape、dtype，以及十输出名称、顺序和 Shape；
- B2 的 INT8 精度评价证据与已知限制。

A4 收到文件后先验哈希和合同，失败时拒绝转换。不得接收随机 ONNX、Mock checkpoint、
人工改名 `.bin`、没有 manifest 的权重或只在聊天中声明“通过”的候选。

## 5. 工具链与环境冻结

每个转换任务必须生成环境 manifest，至少固定：

- OpenExplorer、编译器、量化/校准组件和 Runtime 版本；
- J6P 芯片/板卡型号、BSP、SDK、驱动、固件与 BPU 架构；
- 容器镜像名和不可变 digest，宿主机架构与内核；
- 转换命令、配置文件、环境变量和工作目录；
- source INT8 artifact/manifest SHA256；
- 编译目标、优化等级、输入布局、输入 dtype、batch 和 Shape；
- CPU/BPU fallback、混合精度和自定义算子开关；
- 编译日志、开始/结束时间、退出码和输出文件清单。

“使用最新版”不是可复现版本。没有实际工具链时相应字段写 `UNRESOLVED`，不得推测版本或
预先声称支持。

## 6. OpenExplorer 转换门禁

### G0：来源与环境

- 上游 A2 manifest 和所有哈希匹配；
- 工作区、代码提交、配置与容器身份已记录；
- 输入/输出合同与 A1 固定版本一致；
- 转换使用的实际文件就是 manifest 指向的 candidate。

### G1：图与算子预检查

- ONNX checker、opset、固定 batch/Shape、dtype、输出顺序全部通过；
- 列出每个算子的 OpenExplorer 支持状态、映射结果、精度和执行设备；
- 禁止动态 Shape、动态控制流和未解释的图改写；
- unsupported、fallback、split 或 fused 节点都进入机器可读报告。

遇到算子问题时按以下顺序处理：模型等价改写 → 官方支持的算子组合 → 有证据的混合精度
或 fallback → 确有必要才开发自定义算子。每次改写都回到 A2/B2 做数值和精度复核；A4
不能为了编译通过私自改变 Head 或计划语义。

### G2：编译产物

编译成功必须同时得到：

- J6P 可加载模型文件及 SHA256；
- 完整编译日志和工具退出码；
- 输入/输出 tensor 名、Shape、dtype、layout 和 quant 参数；
- 节点到 CPU/BPU 的映射、fallback 数量及原因；
- 编译器生成的内存、带宽或性能估计（只能标记为估计）；
- source INT8 → compiled artifact 的 manifest 绑定。

只有“命令退出 0”但没有上述证据，不算转换 Gate 通过。

### G3：功能一致性

使用同一批冻结输入，比较 A2 INT8 reference 与编译/Runtime 输出：

- 十个原始输出均可定位，不得丢 Head、换序或错 dtype；
- 输出 Shape、有限值、数值漂移和离散 argmax/计划一致率有原始记录；
- 相同 ModelRequest 生成合法 ManeuverPlan V2；
- request/command ID 回显、1～4 步、target pointer 和失败语义正确；
- PlanValidator 与 SafetySupervisor 仍使用主链实现。

容差和精度 PASS 由 A2/B2 固定，A4 不能根据当前输出临时放宽。

## 7. Runtime CLI 合同

生产 Runtime 必须提供一个无交互入口：

```text
<runtime-command>              # stdin: ModelRequest V1 -> stdout: ManeuverPlan V2
<runtime-command> --describe   # 不推理，只输出身份
<runtime-command> --model-only --input <tensor-dir>
<runtime-command> --trace      # 可选打点，不改变计划
```

正式入口要求：

1. 成功退出码为 0；拒绝、超时、解析或 Runtime 错误为非 0，并在 stderr 给出机器可定位原因。
2. stdout 最后一行是完整计划 JSON，不能混入日志；日志写 stderr。
3. 提供逐行批量或常驻模式，使模型加载与单请求 E2E 可分开。
4. 请求路径复用 A1 的预处理、A3 Adapter 和生产 PlanValidator，不维护第二套实现。
5. 默认 fail closed；坏输入、NaN/Inf、缺图或模型异常不能返回伪成功计划。

可选 trace 使用 `perf_counter_ns` 或等价的高分辨率单调时钟，阶段名固定为：

```text
input_arrival -> preprocess_end -> packing_end -> inference_start
-> inference_end -> postprocess_end -> adapter_end -> plan_ready
```

阶段缺失时应显式缺失，不得用外层时间伪造内部边界；开启和关闭 trace 的计划内容必须一致。
具体字段与可执行检查以 `challenge/hil/a4_runtime_contract.md` 为准。

## 8. 身份查询与 Runtime manifest

`--describe` 至少输出：

- Runtime `git_sha`、`runtime_id` 和启动配置 SHA；
- `model_id/config_id/dataset_version/quantization_id`；
- 板端实际加载模型的 `model_sha256`；
- precision、batch、输入/输出合同；
- OpenExplorer、SDK、Runtime、BSP 和固件版本；
- 目标芯片/板卡、compiled artifact 格式；
- source INT8 manifest SHA、operator mapping SHA；
- CPU/BPU fallback 摘要和已知限制。

最终 `runtime_manifest.json` 还应绑定 `j6p_run.sh`、Dockerfile/镜像 digest、编译日志、
转换配置、契约报告和全部运行依赖。重新编译产生不同字节时必须生成新 runtime ID 和
SHA256，不能覆盖旧身份后沿用旧测量结果。

## 9. 性能测量口径

A4 自测和 B3 复测都要区分：

- 模型纯推理：`inference_start -> inference_end`；
- Planner E2E：`input_arrival -> plan_ready`；
- 冷启动/模型加载：单独报告，不混入常驻单请求数据；
- 预处理、packing、后处理、Adapter/Validator：分别报告；
- batch 固定为 1，warmup 与 measured 样本严格分开。

每次报告至少包含原始样本、P50/P95/P99/max、样本数、warmup、运行轮数、板温、频率/
governor、电源模式、后台负载、Runtime 版本和全部五标识。运行内存要报告 RSS/峰值、
Runtime workspace 和模型驻留口径；功耗要说明整板/SoC/BPU 取电点、采样率和 idle baseline；
CPU/BPU 利用率要记录采样窗口、公式和是否独占板卡。

团队当前门槛：

| 指标 | 门槛/目标 | 说明 |
|---|---:|---|
| 端到端推理 | 官方 ≤200 ms | 以冻结口径和真实板端为准 |
| J6P Planner E2E P95 | 内部 ≤150 ms | 给系统抖动留余量 |
| 运行内存 | 官方 ≤512 MB；内部 ≤450 MB | 口径必须固定 |
| 平均功耗 | ≤25 W | 必须实测，不用 TDP 代替 |
| 异构算力利用率 | ≥80% | 最终公式由 B2/B3 固定 |
| 最终核心性能衰减 | 相对 Teacher ≤3% | 由 B2 精度口径判定 |
| 压缩后 FLOPs 比 | ≤0.5 | 量化文件变小不等于 FLOPs 下降 |

任何单项达标都不能替代其他 Gate。X86 CPU 数字只用于开发趋势，不得填入 J6P 指标。

## 10. 性能优化顺序与禁止项

优化前先锁定功能一致性，再按证据驱动：

1. 消除不必要的 CPU fallback 和设备往返；
2. 复用 buffer，减少 RGB、token、target 和输出张量复制；
3. 固定 Shape 下优化 layout、packing、预处理和后处理；
4. 调整 BPU 任务提交、线程、亲和性、队列和缓存；
5. 控制模型加载、内存峰值、温度和长稳漂移；
6. 每项优化分别比较正确性、P95/P99、功耗、内存与 CPU/BPU 分布。

禁止：按 scenario ID、固定坐标、seed 或测试样本走特殊路径；跳过 Adapter/Validator；改变输入
分辨率或合同却继续沿用旧 Gate；用 batch>1 美化吞吐；只保留最快轮次；把编译器估计当实测；
为降低延迟吞掉 Runtime 错误或输出默认成功计划。

## 11. 证据等级

| 等级 | 最低证据 | 允许声明 |
|---|---|---|
| L0 结构 Smoke | 随机 ONNX、固定 Shape、算子清单 | 结构/工具入口可用 |
| L1 X86 PRE-VALIDATED | 真实 candidate 的请求全链、身份、原始日志 | X86 预验证，不代表板端 |
| L2 OpenExplorer COMPILED | 固定工具链、编译日志、artifact SHA、fallback 报告 | 编译成功，不代表实机达标 |
| L3 J6P FUNCTIONAL | 板端全链、合同 PASS、输出一致性和恢复 | J6P 功能可用 |
| L4 J6P MEASURED | B3 同入口多轮实测、遥测、长稳和原始证据 | 可报告实机指标 |
| L5 RELEASE CANDIDATE | B2/B3 全 Gate、完整 manifest 与可复现包 | 可进入最终挑战赛道候选 |

当前仓库只达到 L0；已有 B3 X86 证据同样基于随机初始化模型，只证明测量机制，不把整体
状态提升为 L1。

## 12. A4 交付给 B3 的包

建议正式布局：

```text
artifacts/a4/<runtime_id>/
├── runtime_manifest.json
├── source_int8_manifest.json
├── openexplorer_env.json
├── conversion_config.yaml
├── compile_command.txt
├── compile.log
├── operator_mapping.json
├── compiled_model.bin
├── j6p_run.sh
├── x86_run.sh
├── Dockerfile
├── contract_report.json
├── consistency_report.json
├── runtime_profile.json
├── hardware_env.json
└── SHA256SUMS
```

B3 接收时应能用 manifest 一次定位实际加载产物、Runtime 提交、启动命令、工具链、输入合同、
fallback、测量配置和所有哈希。大模型/编译产物默认存 artifact storage，不因 Git 路径不同而
失去内容寻址身份。

## 13. 当前可执行检查

现有 X86 结构 Smoke：

```bash
bash challenge/runtime/x86_run.sh
```

这条命令只运行全零输入的 ONNX CPU 前向。正式 Runtime 到位后，先执行：

```bash
python -m challenge.hil.cli artifact \
  --repo . \
  --onnx <gate-passed-int8.onnx> \
  --reference-structure <matching-structure.json> \
  --out <artifact-report-dir>

python -m challenge.hil.cli contract \
  --repo . \
  --frozen challenge/hil/frozen/d2_v1_1_val \
  --adapter board \
  --board-command "<j6p-runtime-command> --trace" \
  --out <contract-report-dir>
```

`contract` PASS 只是测量前置条件，不是精度、延迟、功耗或稳定性 PASS。仓库当前不存在真实
J6P 命令，因此文档只保留占位符，不虚构可运行入口。

## 14. 当前阻塞与完成定义

| 阻塞 | 关闭条件 |
|---|---|
| 无 Gate-passed INT8 输入 | A2/B2 签发可核验候选及完整身份链 |
| 工具链未固定 | 提交 OpenExplorer/SDK/BSP/容器 digest、配置与复现命令 |
| 算子状态未验证 | 用真实工具链更新 operator mapping 与 fallback 报告 |
| 现有 X86 脚本不是生产 Runtime | 实现请求→计划、常驻模式、trace、describe、model-only 和错误语义 |
| 无编译产物 | 生成 J6P artifact、编译日志、manifest 与 SHA256 |
| 无 J6P 入口 | 提供板端启动脚本并通过 A4 Runtime contract |
| 无板端遥测 | 固定功耗、内存、CPU/BPU 采样来源、频率和口径 |
| 无长稳/恢复证据 | 在真实候选上完成多轮、异常、热稳态和恢复测试 |
| 无独立结论 | B3 在同一 Runtime 上复测，B2 汇总精度与最终 Gate |

模块完成的标准是：从同一份 Gate-passed INT8 candidate，在固定工具链中可重复生成字节身份
明确的 J6P 产物；板端 Runtime 完整实现 ModelRequest V1→ManeuverPlan V2、身份查询、打点、
model-only 和常驻模式；没有未解释的 CPU fallback；A4 自检正确性、性能和长稳后，B3 能用
同一入口独立复现原始指标，并把全部结果反向追溯到 source FP32、Calibration、INT8 config、
编译配置和 Runtime 提交。当前仓库尚未达到该状态。

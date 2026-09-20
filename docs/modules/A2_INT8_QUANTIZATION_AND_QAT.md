# A2 INT8 量化、QAT 与精度恢复门禁

## 1. 模块目标

A2 负责把已通过 FP32 Gate 的 Student 转换成适合 J6P 部署的 INT8 候选，建立可复现的
Calibration、PTQ、敏感层分析和量化误差证据；当 PTQ 不能满足精度要求时，A2 与 A3
共同执行 QAT，并把新候选重新交给 B2 独立评价。

A2 不设计 Student 总体结构、不修改 ModelRequest/ManeuverPlan 或十个 Head 合同、不使用
Frozen Test 调参，也不负责 OpenExplorer Runtime、J6P 性能优化或最终实机测量。

相关模块：

- [`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md)：FP32→INT8→Runtime 状态机。
- [`A3_TRAINING_AND_HARD_CASES.md`](A3_TRAINING_AND_HARD_CASES.md)：FP32/QAT 训练职责。
- [`B2_EVALUATION_AND_FP32_GATE.md`](B2_EVALUATION_AND_FP32_GATE.md)：统一评价与 Gate 证据。
- [`challenge/A1_MODEL_INTERFACE.md`](../../challenge/A1_MODEL_INTERFACE.md)：固定 Shape 和 Head 合同。
- [`challenge/hil/README.md`](../../challenge/hil/README.md)：A2 产物的独立结构/一致性检查入口。

## 2. 当前状态快照

核对日期：2026-09-21。代码基线：`challenge` 提交
`89bb1ca7b77eb8cb0cb55529021ed439c7cfbb9a`。

| 能力 | 当前状态 | 代码事实 |
|---|---|---|
| 固定 Shape Student 结构 | 已完成 | batch=1、opset 17、四输入、十输出 |
| FP32 ONNX 结构冒烟 | 已完成 | `challenge/student_v0_fp32.onnx` 为随机初始化 |
| 真实训练权重 ONNX 导出 | 未实现 | `export_onnx.py` 没有 `--weights`，总是重新随机初始化 |
| A3 真实 FP32 Gate 权重 | 未交付 | 没有真实 `A3_FP32_GATE_PASSED` manifest |
| Calibration 正式发布 | 未交付 | 只有 schema/规划，`calibration_frozen=false` |
| PTQ 实现与配置 | 未交付 | 仓库没有 A2 quantization 入口、固定工具版本或 quant config |
| INT8 ONNX/模型 | 未交付 | 仓库中没有 Student INT8 artifact |
| 敏感层报告 | 未交付 | 没有逐层量化或逐 Head 误差证据 |
| QAT | 未实现 | 没有 fake-quant 配置、QAT checkpoint 或训练记录 |
| INT8 通用检查工具 | 部分就绪 | B3 可检查 ONNX 结构并比较两个图的原始输出 |
| OpenExplorer/J6P | 未完成 | 工具链版本、转换配置、板端 artifact 均未交付 |

当前 X86 证据只针对随机初始化 FP32 ONNX，不能推导真实 FP32 精度、PTQ 精度或 J6P
收益。基础赛道使用的 Qwen GPTQ INT4/FP8 与挑战赛道 Student INT8 是两条完全不同的
模型路线，不得复用其权重、revision、延迟或量化结论。

## 3. 正确的量化顺序

```text
A3 FP32 Gate PASS 权重
  -> 从该权重导出固定 Shape FP32 ONNX
  -> PyTorch FP32 与 ONNX FP32 逐输出一致性
  -> 冻结 Calibration release
  -> INT8 PTQ candidate
  -> 结构/算子/原始输出漂移检查
  -> B2 同口径精度评价
  -> PTQ 达标：签发 INT8 candidate
     或 PTQ 不达标：敏感层/混合精度 -> 必要时 A3 QAT
  -> QAT candidate 重新经过全部 Gate
  -> A4 OpenExplorer 转换与 Runtime
  -> B3 X86/J6P/HIL 独立实测
```

Dummy/随机 Student 可用于提前验证命令、算子和文件格式，但产物必须标记 `SMOKE_ONLY`，
不得进入正式精度、体积、性能或 Release Candidate 报告。

## 4. 上游输入合同

### 4.1 A3 FP32 权重

A2 正式 PTQ 只接受：

- `gate_status=A3_FP32_GATE_PASSED` 的权重 manifest；
- 与 manifest 中 SHA256 一致的纯 FP32 `state_dict`；
- 固定 `model_id/config_id`；
- 可定位的 Git SHA、dataset/view/release/Teacher 身份；
- B2 独立 Validation Gate 证据。

`student_fp32_last.pt`、Smoke checkpoint、随机初始化 ONNX、人工改名权重或只有聊天说明的
文件均不允许进入正式量化。

### 4.2 真实 FP32 ONNX

正式 FP32 ONNX 必须从上述同一份 state dict 导出，嵌入并由独立工具核验：

- source FP32 weights SHA256 与 Gate manifest SHA256；
- `model_id/config_id`、dataset version、Git SHA；
- batch=1、四输入固定 Shape、十输出名称/顺序；
- opset 与 exporter/toolchain 版本；
- `weights_status=A3_FP32_GATE_PASSED` 或等价的受控状态。

当前 `challenge/export/export_onnx.py` 不支持加载训练权重，必须先增加受 manifest 约束的
`--weights`/`--weights-manifest` 路径及回归测试。不能通过修改现有随机 ONNX metadata
把它伪装成训练模型。

### 4.3 Calibration release

Calibration 是量化参数调优数据，不是精度 Test。分工要求规模为 300～500 条，由 B1/B2
按独立 split 签发，且必须：

- 不含 Frozen Test、reserved candidate 或 B2 final benchmark；
- 记录 dataset/calibration version、sample/group IDs、RGB 集合和 manifest SHA；
- 覆盖 normal/complex/safety-critical、四路输入动态范围和重要行为/Head；
- 使用与生产完全相同的 A1 preprocessor、归一化、TopK 和 padding；
- batch=1、顺序固定、无随机增强，loader 可重复；
- 记录缺图、NaN/Inf、clip/saturation 与被排除样本，不能静默跳过。

当前仓库只在 schema 中提到 `calibration.jsonl`，现有 manifest 明确
`calibration_frozen=false`，所以正式 Calibration 尚不存在。

## 5. PTQ 配置必须冻结的内容

量化结果不能只写“INT8”。`quant_config` 至少固定：

- 量化框架、OpenExplorer/编译器相关版本和容器/环境指纹；
- source FP32 ONNX/weights/manifest SHA256；
- Calibration release 与 loader Git/config SHA；
- 权重和激活的 bit-width、signed/unsigned、对称/非对称策略；
- per-tensor/per-channel、校准算法、observer 和 clipping 规则；
- 输入/输出 dtype 与 scale/zero-point 处理；
- 保留 FP32/混合精度的层及原因；
- 被融合、重写、fallback 或排除的算子；
- 随机种子、命令行和输出 artifact 路径。

具体策略要由实际 J6P/OpenExplorer 工具链验证后确定，当前仓库不能预设某种配置已受支持。

## 6. 量化后的五级门禁

### G0：来源身份

- FP32 Gate manifest 为 PASS；
- weights、FP32 ONNX 与其 manifest 哈希一致；
- Calibration release 已签发且与 Test 隔离；
- 工作区干净，命令、环境和工具版本已记录。

### G1：FP32 导出等价性

在开始 PTQ 前，用相同冻结请求逐项比较 PyTorch FP32 与 ONNX FP32 的十个原始输出。
Shape、key、输出顺序或数值一致性失败时先修 exporter，禁止通过放大量化容差掩盖导出错误。

### G2：INT8 结构与工具链检查

现有 `challenge.hil.artifact` 可检查 ONNX checker、opset、固定输入 batch/Shape、输出名称
顺序、禁用动态/控制流算子和文件 SHA；当前尚未检查输出 Shape。该 PASS 只表示已有结构
检查成立，不表示量化精度或 J6P 可用。

还必须由 A4 使用真实 OpenExplorer 版本输出 operator/fallback/compile report；X86 ONNX
Runtime 可执行不能替代 OpenExplorer 转换成功。

### G3：数值漂移与敏感层

用同一冻结请求比较 FP32 ONNX 与 INT8 候选的全部 Head，至少报告：

- 每个输出的 max/mean absolute error、分位数和异常样本；
- 离散 Head 的 argmax/计划一致率；
- target speed MAE 增量；
- 激活 clipping/saturation 比例；
- 按层恢复 FP32 后的误差变化和敏感层排名。

B3 `consistency` 默认 `rtol=1e-4, atol=1e-5` 是 FP32 图等价性口径，对 INT8 通常过严；
CLI 虽允许改容差，但最终阈值必须由 B2 policy 固定，不能现场调到“刚好通过”。Raw tensor
allclose 也只是诊断，不能替代真实标签上的准确率 Gate。

### G4：B2 INT8 精度 Gate

同一冻结评价集和相同指标实现比较 Teacher、FP32 与 INT8：

- 团队内部目标：INT8 相对 Teacher 的累计核心性能衰减不超过 2%；
- PTQ 相对已通过的 FP32 额外下降超过 1% 时触发 QAT 评审；
- safety-critical recall 不能被总体平均掩盖，出现明显下降即阻塞；
- schema validity 必须 100%；
- Behavior、target、lane、speed、completion、plan sequence 和逐场景类别分别报告。

最终 J6P 相对 Teacher 的累计核心性能衰减官方上限为 3%；INT8 Gate 通过不代表 J6P
最终 Gate 已通过。

### G5：下游交接

只有 G0～G4 全部通过的 INT8 candidate 才能交给 A4 转换。A4/B3 使用的每个 ONNX、
`.bin` 和 Runtime 都必须反向绑定同一 INT8 manifest；重新转换产生新字节时要记录新的
artifact SHA，不能继续引用导出前 ONNX 的 SHA。

## 7. 敏感层分析

敏感层分析不是“看哪层名字像关键层”，而是固定 Calibration 和评价集后做受控实验：

1. 全 INT8 PTQ 作为 baseline；
2. 每次只把一层/一组算子恢复到高精度；
3. 比较逐 Head、计划一致率、速度 MAE、安全切片和 saturation；
4. 记录精度收益、延迟/内存代价和 OpenExplorer 支持状态；
5. 只保留能稳定改善目标指标的混合精度例外。

`sensitive_layers.md` 至少列出节点/模块名、输入输出范围、量化策略、误差、受影响 Head、
尝试方案、最终精度和保留理由。禁止为追求总体平均值牺牲 STOP/YIELD/避障等安全行为。

## 8. QAT 触发与 A2/A3 交接

满足任一条件进入 QAT 评审：

- PTQ 造成核心指标额外下降大于 1%；
- safety-critical recall 明显下降；
- 某个关键 Head 出现系统性偏差；
- 合理的混合精度仍不能达到 Gate。

### A2 → A3

A2 提供冻结的 fake-quant/observer 配置、source FP32 与 PTQ SHA、Calibration manifest、
敏感层报告、逐 Head 误差、失败 sample IDs 和目标 INT8 导出路径。A3 不应自行猜测 A2
工具链的量化节点。

### A3 → A2

A3 只使用 Train/Val 进行 QAT 和模型选择，输出新的 checkpoint、训练日志、逐 Head 指标、
hard cases 与 QAT manifest。Frozen Test 继续不可见。A2 必须从该精确 checkpoint 重新
导出量化产物，并重新执行 G0～G4；旧 PTQ 结果不能沿用。

QAT 后若结构、preprocessor、Head 或枚举发生改变，应回到 A1 合同版本升级，而不是让
A2/A3 私下产生不兼容分支。

## 9. 正式交付包

建议正式交付布局：

```text
artifacts/a2/<quantization_id>/
├── calibration_manifest.json
├── calibration_config.yaml
├── quant_config.yaml
├── source_fp32_manifest.json
├── student_int8.onnx
├── int8_structure.json
├── int8_manifest.json
├── artifact_report.json
├── raw_output_drift.json
├── quant_error_report.json
├── sensitive_layers.md
├── qat/                       # 仅实际使用 QAT 时存在
└── commands.txt
```

`int8_manifest.json` 至少绑定：

- `quantization_id`、Git SHA、工具链和环境；
- source FP32 model/config/weights/ONNX/Gate manifest SHA；
- Calibration version/manifest/config SHA；
- quant config SHA、INT8 artifact SHA/大小/格式；
- B2 evaluation/policy manifest SHA 与 Gate 状态；
- 是否 PTQ/QAT、混合精度层列表和已知限制。

产物默认进入 `artifacts/`；在 B2 Gate 和交接审查前不提交大型权重到 Git。

## 10. 当前可以执行的检查

拿到真实 FP32/INT8 ONNX 后，现有通用工具可先执行：

```bash
# 结构、固定 Shape、输出顺序、算子和文件 SHA
python -m challenge.hil.cli artifact \
  --repo . \
  --onnx artifacts/a2/run/student_int8.onnx \
  --reference-structure artifacts/a2/run/int8_structure.json \
  --out artifacts/a2/run/artifact_report

# FP32 ONNX 与 INT8 ONNX 的十个原始输出对比
python -m challenge.hil.cli consistency \
  --repo . \
  --baseline-onnx artifacts/a2/run/student_fp32.onnx \
  --onnx artifacts/a2/run/student_int8.onnx \
  --frozen challenge/hil/frozen/d2_v1_1_val \
  --limit 100 \
  --out artifacts/a2/run/raw_output_drift.json
```

第二条当前只能作开发诊断：使用的是 D2 development Val 快照，并且默认 FP32 容差不构成
INT8 Gate policy。第一条也要求 A2 为该 INT8 文件生成匹配 SHA 和算子集的
`int8_structure.json`；若省略，CLI 会默认拿随机 FP32 的 `model_structure.json` 对比并
正确报错。仓库目前没有可执行的正式 PTQ/QAT 命令，文档不能虚构量化已跑通。

## 11. 量化与压缩指标边界

- INT8 降低权重/激活存储和可能的运行开销，但通常不改变网络 FLOPs 数；不能用文件变小
  代替官方 `压缩后 FLOPs / 原始 FLOPs ≤ 0.5`。
- X86 加速不等于 J6P 加速；CPU EP、桌面 GPU、BPU 的算子映射和数据搬运不同。
- OpenExplorer 转换成功不等于全部算子在 BPU；CPU fallback 必须由 A4 报告并由 B3 实测。
- INT8 accuracy PASS 不等于闭环、安全、延迟、内存、功耗或异构利用率 PASS。
- Calibration 上误差低不等于独立 Benchmark 上精度保持。

## 12. 当前阻塞与完成定义

| 阻塞 | 关闭条件 |
|---|---|
| 无真实 FP32 Gate 权重 | A3/B2 签发可核验的 FP32 PASS 权重与 manifest |
| exporter 总是随机初始化 | 支持受 manifest 约束的训练权重导出并增加逐输出回归 |
| Calibration 未冻结 | B1/B2 发布 300～500 条专用 split、loader、manifest 和覆盖报告 |
| 无 A2 工程 | 提交 PTQ、配置、敏感层、报告、manifest 和自动化测试入口 |
| 无固定量化工具链 | 锁定版本、容器/环境、命令和 OpenExplorer 对接边界 |
| 无 INT8 policy | B2 固定逐 Head/切片/累计衰减/空分母和失败处理规则 |
| 无真实 INT8 artifact | 从 Gate-passed FP32 生成、核验并签发候选 |
| 无 QAT 闭环 | 仅在触发条件满足时完成 A2/A3 交接、训练、重新量化和重评 |
| 无 J6P 证据 | A4 转换并由 B3 在真实板端独立测量，不能用 X86 代替 |

模块完成的标准是：从一个可追溯的 FP32 Gate 权重和冻结 Calibration，在干净环境中可重复
生成字节身份明确的 INT8 候选；逐 Head 数值漂移、敏感层和 B2 精度下降都有原始证据；
QAT 是否触发有固定规则；下游 OpenExplorer/J6P artifact 能反向追溯到同一 source FP32、
Calibration 和 quant config。当前仓库尚未达到该完成状态。

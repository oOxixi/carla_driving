# B1 数据发布到 A3 蒸馏接入

## 1. 模块目标

本模块把 B1 生成的真实 Qwen Teacher 数据转换成 A3 可以审计、训练和复现的 Student
监督视图。它不负责采集数据、不修改 B1 原始发布包、不读取 Frozen Test，也不负责 B2
最终判分。

链路固定为：

```text
B1 immutable release
  -> 发布完整性与 Teacher provenance 校验
  -> A3 strict-positive 派生视图
  -> A1 四模态输入与标签 Shape 校验
  -> Train/Validation 预检
  -> Student FP32 训练与 best checkpoint
  -> 独立 Validation Teacher/Student 对比
  -> A3_FP32_GATE_PASSED 或失败
```

任何一步没有可核验的 manifest 和 SHA256，后一步都不能把结果表述为正式训练或精度结论。

## 2. 当前状态快照

核对日期：2026-09-24。实现基线从 `challenge` 提交 `1f97aa1e` 开始，最终提交以本页
所在提交为准。

| 数据发布 | 状态 | A3 当前允许用途 |
|---|---|---|
| `d2_v1_1` | `B1_SIGNED_PASS` | 已支持派生严格正样本视图、预检、Smoke 和正式基线训练 |
| `d3_wave1_addon_v1` | immutable candidate + detached `B1_SIGNED_PASS` | 允许通过累积门禁进入 D2+D3 正式训练输入 |
| D2 reserved/test candidates | B1/B2 保留 | A3 不读取、不调参、不选 checkpoint |

D3 Wave1 是叠加在 D2 v1.1 上的增量包，不覆盖也不重写 D2。发布中包含 1747 条 Train
增量、308 条 Val 增量、308 条 hard negative、35 条隔离记录和 2363 张 RGB。本地可只做
`--skip-images` 元数据开发检查；正式门禁固定在服务器完整副本上验证全部 RGB，不能用
跳图结果启动正式训练。

## 3. 上下游合同

### 3.1 B1 必须交付

正式发布至少包含：

- 不可变的 Train、Validation 和隔离池 JSONL；
- 每条记录唯一的 `sample_id`、`request_id` 和 `group_key`；
- 合同有效的 `ModelRequest V1` 和 `ManeuverPlan V2`；
- 可移植 RGB 路径、逐图 SHA256、映射清单和图片集合哈希；
- `scenario_family + map + route_hash + seed` 的分组切分证据；
- Teacher `model_id`、精确 revision、模型 artifact fingerprint 和采集代码身份；
- run、command、plan、场景验收四类终态一致的闭环质量字段；
- 发布 manifest 的文件字节数、SHA256、签发状态和数据版本。

普通正监督必须同时满足：

```text
quality.valid_for_training == true
quality.training_role == POSITIVE
closed_loop_quality.run_status == SUCCEEDED
closed_loop_quality.command_terminal_status == SUCCEEDED
closed_loop_quality.plan_terminal_state == SUCCEEDED
closed_loop_quality.scenario_acceptance_passed == true
```

不满足条件的记录必须进入 hard-negative 或 quarantine，不能通过 A3 本地过滤后悄悄混入
普通正样本。

### 3.2 A3 必须交付

A3 不直接编辑 B1 发布文件，而是在 `artifacts/` 生成派生视图及其 manifest：

- 固定 Train/Validation 成员关系；
- 记录保留、排除的 sample ID 和原因；
- 将 Teacher 精确身份补入每条派生记录；
- 保存源 release manifest、各 Teacher cohort manifest 和派生文件 SHA256；
- 验证 A1 的四路输入、TopK=8、`NONE=8`、最大四步和十个 Head 标签；
- 拒绝 Train/Validation 的 sample、request、group 或规范化记录重叠；
- 输出 checkpoint、纯 state dict、训练日志、逐 Head 指标和 hard cases；
- 在 B2 提供独立 Validation 对比前保持 `PENDING_A3_FP32_GATE`。

### 3.3 B2 与 B3 边界

- B2 冻结独立评价样本和判分口径，A3 只接收聚合评价证据，不读取 Frozen Test 样本。
- B3 消费带 `A3_FP32_GATE_PASSED` 的 FP32 权重与 manifest 做 x86/HIL 验证。
- B3 对现有 D2 Val 的回放只能证明工具链可运行，不能替代 B2 独立泛化结论。

## 4. 已完成的 D2 与 D2+D3 路径

当前保留 D2 v1.1 单发布回归路径，并新增互不覆盖的 D2+D3 累积路径：

| 责任 | 实现 |
|---|---|
| B1 发布校验 | `challenge/dataset/validate_d2_release.py` |
| A3 严格正样本派生 | `challenge/dataset/build_a3_d2_view.py` |
| 标签覆盖审计 | `challenge/distillation/audit_d2_view.py` |
| A1 输入打包校验 | `challenge/distillation/validate_a1_inputs.py` |
| 数据预检 | `challenge/distillation/preflight.py` |
| 正式配置 | `challenge/distillation/d2_v1_1_formal_config.yaml` |
| 训练、断点与候选导出 | `challenge/distillation/train.py` |
| FP32 晋级 | `challenge/distillation/promote.py` |
| D3 旁路签名与发布校验 | `challenge/dataset/validate_d3_release.py` |
| D2+D3 严格正样本派生 | `challenge/dataset/build_a3_cumulative_view.py` |
| 累积视图全量审计 | `challenge/distillation/audit_cumulative_view.py` |
| 累积正式配置 | `challenge/distillation/d2_d3_cumulative_formal_config.yaml` |

已验证的 A3 D2 严格正样本视图为 Train 2332、Val 489。该 Val 与 Train 的指令文本和
场景 ID 高度重合，因此它只用于开发回归和同分布模型选择，不能证明未见指令或未见场景
泛化。详细结果见 `challenge/distillation/D2_FP32_BASELINE_FINDINGS.md`。

训练与promotion的identity policy已经统一：`signed_d2_release_formal` 会严格核对
release/view SHA，并要求B2评价携带一致的benchmark/policy SHA、case-set digest、
evaluator Git SHA、样本数，逐端绑定predictions SHA并绑定Student权重SHA；正式Teacher
对照固定为v4。当前仍没有B2真实独立Validation包，所以这只是关闭代码合同阻塞，不代表已有候选
晋级。剩余完成定义见
[`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md#6-fp32-晋级门禁)。

标准复现顺序：

```bash
python -m challenge.dataset.validate_d2_release
python -m challenge.dataset.build_a3_d2_view
python -m challenge.distillation.audit_d2_view
python -m challenge.distillation.validate_a1_inputs
python -m challenge.distillation.train \
  --config challenge/distillation/d2_v1_1_smoke_config.yaml \
  --integration-smoke
python -m challenge.distillation.train \
  --config challenge/distillation/d2_v1_1_formal_config.yaml
```

D2+D3 累积输入复现顺序：

```bash
python -m challenge.dataset.validate_d3_release
python -m challenge.dataset.build_a3_cumulative_view
python -m challenge.distillation.audit_cumulative_view
python -m challenge.distillation.validate_a1_inputs \
  --release-dir challenge/dataset/releases/d2_v1_1 \
  --d3-release-dir challenge/dataset/releases/d3_wave1_addon_v1 \
  --view-dir artifacts/a3_d2_d3_cumulative_positive_view_v1 \
  --asset-root .
python -m challenge.distillation.train \
  --config challenge/distillation/d2_d3_cumulative_smoke_config.yaml \
  --integration-smoke
python -m challenge.distillation.train \
  --config challenge/distillation/d2_d3_cumulative_formal_config.yaml
```

正式训练要求干净 Git 提交、完整 RGB 和 CUDA/PyTorch 环境。没有这些条件时只运行只读
清单审计，不生成可晋级权重。

## 5. D3 Wave1 接入分析

### 5.1 已经成立的部分

- 发布采用 additive 语义，未修改 D2 v1.1。
- Train/Val/hard-negative/quarantine 角色已分开。
- 35 条终态不一致的伪正样本已隔离。
- JSONL、RGB mapping、split、provenance 和 release manifest 已提供。
- 文件数量和 Git blob 字节数与 `release_manifest.json` 中的声明一致。

元数据复核结果：Train 增量 1747 条、Val 增量 308 条；两侧 `sample_id` 和
`request_id` 均各自唯一，Train/Val `group_key` 重叠为 0，全部 2055 条都满足发布中
声明的普通正样本与闭环成功条件。服务器已经完成 2363 张 D3 RGB 的逐图哈希及完整
release/view 审计；A1 全量打包结果必须继续单独记录，不能由元数据结果代替。

### 5.2 已关闭的接入阻塞与仍保留的证据边界

| 项目 | 当前代码事实 | 结论 |
|---|---|---|
| 旁路签发 | `B1_SIGNED_PASS.json` 绑定 immutable manifest、integrity report、lock、RGB set 和 Teacher v4 | 已由独立 validator 接入 |
| 多发布身份 | `signed_cumulative_release_formal` 与独立 view version | 已与 D2 单发布隔离 |
| D3 cohort | v0.5 映射到 pinned Teacher v4 manifest | 派生记录补齐精确 provenance |
| 全量 RGB | 服务器逐图核验 D2 3592、D3 2363 | 输入完整性 PASS；本地跳图不能替代 |
| 普通监督 | 累积 Train 4079、Val 797 | 可进入正式训练预检 |
| hard negative | D3 308 条仅进入排除审计索引 | 当前不作为普通监督；后续需专门 loss/采样设计 |
| 独立泛化 | D3 未增加新 source text/scenario ID，官方 manifest 也声明 development only | 仍不能作为 unseen/template-disjoint Gate |
| 关键覆盖 | Town03_Opt、YIELD、PULL_OVER、HOLD、三步、四步仍未由本次接入证明补齐 | 仍需 B1/B2 后续数据与独立评价 |

D3 采集记录中的 `metadata.teacher_git_sha` 为
`95e97b00def8ec36f12937da34ce8bb9082c4a04`。该字段表示采集代码身份，不能直接替代
`challenge/teacher_baseline_manifest.json` 中冻结的早期 Teacher 基线身份。旁路签名已经绑定
`challenge/teacher_pinned_manifest_v4.json`；A3 派生器据此注入模型 revision 和 artifact
fingerprint，同时保留采集 SHA，二者不再混用。

### 5.3 Windows 文本哈希注意事项

仓库当前继承全局 `core.autocrlf=true`。JSON/JSONL 在 Windows 工作区可能由 LF 转成
CRLF，导致工作区原始字节 SHA256 与 Linux 生成的发布 manifest 不同；Git blob 字节数
仍与发布声明一致。这不是允许忽略哈希，而是说明正式验证应在固定换行策略的干净工作区
进行，或为发布数据声明 `.gitattributes` 的 `eol=lf` 后重新签发。不能把换行转换后的文件
哈希失败误报成 B1 内容被修改。

## 6. D3 数据接入与后续训练完成定义

数据接入的第 1～5 项已经由代码与服务器证据关闭；第 6～7 项仍是正式训练和晋级工作：

1. B1 旁路签名、Teacher revision/fingerprint 与采集 provenance：**完成**。
2. 2363 张 D3 RGB 的逐图 SHA、图像集合、引用门禁：**服务器完成**。
3. additive 派生器绑定 D2/D3/signature/source evidence：**完成**。
4. Train/Val sample/request/group/record 隔离和全量预检：**门禁已实现**。
5. 独立 config ID、view version、输出目录和自动化测试：**完成**。
6. 全量 A1 输入打包、标签编码、Smoke、断点恢复和重复运行一致性通过。
7. D3 Val 只标记为 development validation；在 B2 交付独立 Seen/Variant/Unseen
   评价前，不生成泛化通过结论。

## 7. 当前可以做与不能做

| 操作 | 当前结论 |
|---|---|
| 阅读 D3 README、manifest 和 JSONL | 可以 |
| 核对条数、schema、终态治理和切分字段 | 可以 |
| 分析标签覆盖和缺失类别 | 可以；结论只针对 development 数据 |
| 使用 D2 v1.1 复现既有 A3 基线 | 可以 |
| 通过累积派生视图和正式门禁启动 D2+D3 训练 | 可以；必须是干净提交且完整 RGB |
| 用 D3 Val 宣称泛化或比赛准确率 | 不可以 |
| 用 reserved/test candidates 调参 | 不可以 |
| 生成 `A3_FP32_GATE_PASSED` | 不可以，仍缺 B2 独立对比证据 |

## 8. 文档维护规则

- 数据状态只引用 release manifest，不根据聊天记录或文件夹名称推断。
- 训练状态只引用 run summary、checkpoint SHA 和 candidate manifest。
- “Smoke 通过”“训练完成”“FP32 Gate 通过”“B2 最终通过”必须分开表述。
- 新 release 不覆盖旧文档中的历史数值；新增一节或新版本文档并记录提交 SHA。
- 实现变化后同时更新本页、模块 README 和相关测试，禁止只改说明不改门禁。

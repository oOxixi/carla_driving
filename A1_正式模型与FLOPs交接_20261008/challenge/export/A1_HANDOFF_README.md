# A1 正式模型接口与 FLOPs 交接（2026-10-08）

本包交付 A1 能独立确认的结构、接口和可复算算量。不是整队最终评测包，不替代 A3 训练权重、A2/A4 板端产物或 B2/B3 实测。

## 可供报告直接引用

Student 为 `StudentPlannerV0`（`student-v0-r3-fp32`），参数量 23,006,581。固定 batch=1，输入 RGB `[1,3,224,224]`、文本编码 `[1,32]`、目标 `[1,8,14]`、车辆/场景状态 `[1,64]`，均为 float32。输出最多 4 步的 10 个结构化 Head；输出经 Adapter 形成 ManeuverPlan V2，不直接输出油门、制动或轨迹点。

Student 的 Conv2D/Linear 算量为 249,320,448 MACs，即 **498,640,896 FLOPs（0.498640896 GFLOPs）/次**，约定 1 MAC=2 FLOPs，不含其他算子或前后处理。

候选原始模型采用已有固定 Teacher `Qwen/Qwen3.5-2B`，revision `15852e8c16360a2fea060d615a32b45270f8a8fc`。本次按其实际 24 层混合注意力配置和 Transformers 模块尺寸复算，不再使用旧的通用 28 层分母。固定 ModelRequest 样例经当前生产提示词与本地处理器形成 267 个 prefill token，其中视觉 token 为 64；输入是明确声明的 224×224 纯黑结构测试图片，处理器网格为 `[1,16,16]`。一次 prefill 加末位置 logits 生成 1 个受约束动作码，Conv/Linear 核心算量为 **892,929,605,632 FLOPs（892.929605632 GFLOPs）**。

两者同一模型内 Conv/Linear 口径下的参考比值为 **0.0005584325（0.05584325%）**。此比值仅用于结构分析：不是完整网络算子 FLOPs，也不是正式比赛的已批准分母；不得据此直接声称获得 FLOPs 档位分数或整队通过 Gate。Teacher 输入保留更长提示词，而 Student 为固定 32 字符编码；两者是否属于评委认可的等价工作量仍须团队确认。

Teacher 未计注意力 QK/AV、gated-delta 递推、归一化/激活/逐元素运算等；Student 未计池化、偏置、激活等。两端均不计 ASR/NLU、图像预处理、提示词拼接、Adapter、安全层和控制器。因此这是**模型内密集 Conv/Linear 运算量**，不是语音端到端计算量。INT8/FP32 或文件大小变化不等于 FLOPs 下降。

## 文件入口

| 内容 | 文件 |
|---|---|
| 模型及初始化 | `challenge/student/model.py`、`challenge/student_config.json` |
| forward 输入/输出、类别及 padding/mask | `challenge/A1_MODEL_INTERFACE.md`、`challenge/a1_interface_verified.json` |
| 可执行类别、padding、loss mask | `challenge/student/contract.py`、`challenge/student/training_contract.py` |
| 输入预处理、输出解码、模型后端 | `challenge/student/preprocess.py`、`challenge/planner/` |
| Student 算量及逐模块 MACs | `challenge/flops_report.json` |
| 各候选分母与计数范围的直接数值、条件档位 | `challenge/flops_options.json`、`challenge/export/flops_options.py` |
| Teacher 配置、token 工作量、304 个密集模块及算量 | `challenge/export/teacher_config_pinned.json`、`challenge/teacher_flops_report.json` |
| 原 Teacher 身份证据 | `challenge/teacher_baseline_manifest.json`、`challenge/teacher_pinned_manifest.json` |
| 结构导出与 ONNX 元信息 | `challenge/export/export_onnx.py`、`challenge/model_structure.json`、`challenge/student_v0_fp32.onnx` |
| 最小复核及原始输出 | `challenge/export/verify_a1.py`、`logs/` |
| 文件完整性 | `manifest.json`、`verify_manifest.py` |

`student_v0_fp32.onnx` 是已有随机初始化的结构 smoke，**不能用于最终准确率、仿真或板端性能结论**。A3 应交付正式训练权重和 manifest；相同结构的 FLOPs 不随权重数值改变。Teacher 元数据/Tokenizer 在 `teacher_metadata/`，不包含 4.55 GB 权重，形状分析不需要加载权重。固定权重的获取由原 Teacher manifest 指定。

## 最小复现（Python 必须为 3.12）

在本目录运行。已验证 Student 环境：Python 3.12，Torch 2.6.0+cu124；Teacher 元数据分析环境：Python 3.12.3、Torch 2.12.1+cu132、Transformers 5.14.1，均使用 CPU，不需要 CUDA/GPU。两套分析环境不是部署环境要求，未修改现有训练、A800 或板端配置。完整实际版本见 `environment.json`。

```powershell
py -3.12 verify_manifest.py
py -3.12 -m challenge.export.verify_a1 --output reproduced_interface.json
py -3.12 -m challenge.export.compute_flops --output reproduced_student_flops.json
py -3.12 -m pytest -q challenge/tests/test_a1_student.py challenge/tests/test_flops_denominator.py
```

预期接口检查 PASS、Student FLOPs=498640896、21 tests passed。Student 环境依赖见 `challenge/requirements.txt`（pytest 另装）；无需安装 OpenAI 客户端或启动模型服务。

在具备所记录 Transformers/Torch 的 Python 3.12 环境复算 Teacher：

```text
python -m challenge.export.teacher_flops --model-dir teacher_metadata --output reproduced_teacher_flops.json
```

预期 267 prefill tokens、64 visual tokens、core_flops=892929605632。纯 meta 构造，不加载真实权重、不联网、不证明模型预测正确。完整提示词、输入 token IDs 和各模块的尺寸与计算式保存在报告中；不同请求长度会改变 Teacher 算量，不能套用本样例常数到整个数据集。

`model_structure.json` 和新 Student 报告保留原 ONNX 的 source_git_sha，以保持产物身份一致；`analysis_source_git_sha` 另记本次分析的基线。此次未提交修改的源文件以 manifest 中 SHA256 为准，不能只凭 Git HEAD 认为是原样代码。

## 报告负责人可选口径：直接数值已给出

以下均为 batch=1；不使用单 token 保守下界作为主结果。压缩比为“优化后模型运算量 / 原始模型运算量”，百分比与小数不要混用。

| 候选原始模型 / 范围 | Student（GFLOPs） | 原始模型（GFLOPs） | 比值 | 比值百分数 | 口径获认可时的条件档位 |
|---|---:|---:|---:|---:|---|
| 固定 Teacher；Conv/Linear | 0.498640896 | 892.929605632 | 0.0005584325 | 0.05584325% | ≤0.5，15 分档 |
| 固定 Teacher；拓展主算子，参考算法解析计算 | 0.498640896 | 911.695101952 | 0.0005469382 | 0.05469382% | ≤0.5，15 分档 |
| 初审整理包里的同结构 FP32 Student；Conv/Linear | 0.498640896 | 0.498640896 | 1.0 | 100% | >0.9，不取得该项档位分 |
| 同结构 FP32 Student；完整 forward 抽象浮点算术口径 | 0.499437133 | 0.499437133 | 1.0 | 100% | >0.9，不取得该项档位分 |

条件档位只说明“若对应原始模型及范围被认可”的数值所在档位，不代表评委已经批准。`formal_ratio_pass` 和 `ratio_pass` 仍为 null。无需报告负责人再计算这些比例，可从 `flops_options.json` 选择所需行；不要把不同范围的分子和分母交叉拼接。

### 拓展主算子如何计算

在固定 Teacher 的 Conv/Linear 基础上增加：视觉注意力 QK/AV **6.442450944 GFLOPs**、文本注意力 QK/AV **3.503996928 GFLOPs**、gated-delta 状态递推核心 **8.819048448 GFLOPs**，合计 **911.695101952 GFLOPs**。

计算式：视觉 `4 × 24 × 256² × 1024`；文本 `4 × 6 × 267² × 8 × 256`；递推核心 `7 × 18 × 267 × 16 × 128 × 128`。注意力按密集参考算法计算，递推按逐 token 参考算法的衰减、读取、delta 更新、秩一更新与输出读取计算。真实 vLLM prefill 使用的 chunk/fused 内核可能不同，因此这行是**模型参考算法解析算量，不是实际服务内核 Profiler 结果**。

这行仍未包含 Teacher 的 softmax、norm、rotary、门控、残差、激活、偏置等；不能把 911.6951 GFLOPs 标为“完整网络所有算子实测值”。相比上一版增加的是统计覆盖，不是模型本身性能提升。真实服务延迟、精度和模型结构本轮未改变。

Student 完整 forward 的抽象浮点算术量为 **499,437,133**：Conv/Linear 498,640,896 + 偏置/池化/功能性激活等 796,237。MAC=2；加减乘除各 1；Sigmoid 采用负号、exp、加、除共 4 次抽象运算（exp 按 1 次计，不等于硬件指令数）。ReLU 的 782,208 次比较另列、不计为浮点算术；将比较也计入的等价总量为 500,219,341。reshape、cat、数据搬运不计 FLOPs。详细逐层输出尺寸和分项均在 JSON 中。

### “初赛模型”并不只有一种含义

本地 `初审提交_20261005` 的 `release_manifest.json` 明确记录模型为 **Qwen3.5-2B**，revision 与固定 Teacher 完全一致；如果报告团队选择这个模型作为“初赛原始模型”，在同一请求与同一计数范围下，应使用上表 Teacher 两行的数值，**不是 1.0**。

同一整理包还包含挑战赛道 Student 结构快照；其 `model.py`、`contract.py` 与当前源码经换行规范化后完全一致。所以仅当报告团队把这个 FP32 Student 选作“原始模型”，且优化后仍是同结构时，比值才为 **1.0**。仅从 FP32 量化为 INT8 不会减少网络 MAC 次数，量化的存储/延迟收益应另列。

初审目录的状态是 `STAGED_NOT_READY`，证明的是整理材料身份，不能据此断言已经正式提交了哪个模型。原始证据已经附在 `baselines/initial_prepared_package/`，选择权交给报告负责人。本包已提供这些候选所能复算的直接数值；**Teacher 完整网络所有算子的精确总量尚无实测证据，不填写虚构总数**。若最终按该范围计分，仍需双方统一的算子 profiler/完整解析计数；若 A2/A4 改变网络结构，重新计算分子。

复算候选表：

```powershell
py -3.12 -m challenge.export.flops_options --output reproduced_flops_options.json
```

本轮不重训、不重跑 CARLA、不宣称新的精度/延迟/板端 Gate。交接包含四个直接比较选项、初审材料身份、逐项算量与复算入口，供报告负责人据规则选择。

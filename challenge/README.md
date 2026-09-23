# 挑战赛道 A1：轻量 Student 结构

全挑战赛道（B1 数据、A3 训练、A4 部署与 B3 HIL）统一导航见 [挑战赛道模块](../docs/architecture/modules/challenge.md)。本页主体保留 A1 结构交付说明，不代表整个挑战赛道只实现了 A1。

本目录只替换高层 Planner：`ModelRequest V1 → PlannerBackend → ManeuverPlan V2`。
现有 A/B/C/D 控制、安全接口和 CARLA 输入均保持不变。

当前交付为可训练的 Student V0 结构和随机初始化固定 Shape ONNX，**不是已蒸馏权重，
也不是 J6P、精度或延迟达标结论**。A3 训练后通过相同结构加载权重，A2/A4 分别完成
量化与板端转换。

## 固定环境

- Python 3.12
- PyTorch 2.6
- ONNX opset 17
- batch 固定为 1，不使用 `dynamic_axes`

## 最小验证

```powershell
py -3.12 -m pip install -r challenge/requirements.txt
py -3.12 -m pytest -q challenge/tests/test_a1_student.py
py -3.12 -m challenge.export.export_onnx --output challenge/student_v0_fp32.onnx
py -3.12 -m challenge.export.validate_artifacts --root .
```

导出命令会同时更新输出目录内的 `model_structure.json` 和 `flops_report.json`，
统一记录实际 ONNX SHA256 与导出代码的 Git SHA，无需手工编辑报告。
默认记录当前 HEAD；复现已发布版本时，先检出报告中的 `source_git_sha` 再运行导出。
`--source-git-sha` 仅用于显式记录已核对的导出代码版本，不会自动切换代码。

对接 A2/A3/A4 时以 `A1_MODEL_INTERFACE.md` 为统一入口；结构与压缩依据见
`student_architecture.md`。Teacher 的代码与模型版本见 `teacher_baseline_manifest.json`。
Student 只有在权重 manifest 的模型 ID、SHA256 和 `A3_FP32_GATE_PASSED` 均通过校验后
才会报告 production-ready，不能通过手工布尔参数绕过 Gate。
清单必须是 JSON 对象，所有必需字段为非空字符串，`git_sha` 为完整 40 位十六进制值；
`config_id` 必须与当前模型配置一致。此校验检查交付身份与声明，不代替 B2/B3 独立验收。

## A3 蒸馏

A3 已在 `challenge/distillation/` 对接本 Student V0 r3 的四路输入、十个输出
Head、固定类别映射和纯权重交付格式。入口、数据预检、训练、断点恢复、Hard-case
和 FP32 Gate 说明见 `challenge/distillation/README.md`。Mock Smoke 产物始终标记
为 `MOCK_ONLY`，不得作为可部署权重。

## A2 量化

A2 的正式输入必须是 Gate-passed FP32 权重及由该权重导出的 ONNX；当前仓库 ONNX 是
随机初始化结构冒烟产物，不能用于正式 PTQ。Calibration、PTQ/QAT、INT8 Gate 和交接
要求见 [`docs/architecture/modules/A2_INT8_QUANTIZATION_AND_QAT.md`](../docs/architecture/modules/A2_INT8_QUANTIZATION_AND_QAT.md)。

## A4 部署

A4 只接收身份完整且通过精度门禁的 INT8 candidate。OpenExplorer 转换、算子/fallback
审计、X86/J6P Runtime 接口、性能优化顺序、证据等级和 B3 交接要求见
[`docs/architecture/modules/A4_OPENEXPLORER_J6P_RUNTIME.md`](../docs/architecture/modules/A4_OPENEXPLORER_J6P_RUNTIME.md)。
当前随机初始化 FP32 ONNX 和全零输入 X86 计时仅是结构 Smoke，不代表 J6P 可部署或达标。

## B3 独立实测

B3 只测 A4 交付的同一 Runtime，不修改模型或维护第二套测试实现。HIL 回放、八阶段计时、
Seen/Variant/Unseen、板端遥测、长稳、证据等级和最终门禁见
[`docs/architecture/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md`](../docs/architecture/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md)。
当前策展结果仅为随机初始化模型的 X86 机制预验证，不属于正式 J6P 结果。

## B4 复现与交付

B4 负责把代码、数据、模型、Runtime、B2/B3 原始证据和 Docker 绑定到唯一 Release
Candidate，并在干净环境复现后生成 Final 包。详细状态机、Manifest、冻结和 G5 门禁见
[`docs/architecture/modules/B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md`](../docs/architecture/modules/B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md)。
当前基础赛道 Qwen 打包脚本不能替代挑战赛道 Student/J6P 发布链。

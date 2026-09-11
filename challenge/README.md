# 挑战赛道 A1：轻量 Student 结构

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

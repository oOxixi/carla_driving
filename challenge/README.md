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
py -3.12 -m challenge.export.compute_flops --output challenge/flops_report.json
py -3.12 -m challenge.export.export_onnx --output challenge/student_v0_fp32.onnx
```

输入 Shape、输出顺序和 Adapter 映射见 `student_shape_contract.md`；结构与压缩依据见
`student_architecture.md`。Teacher 的代码与模型版本见 `teacher_baseline_manifest.json`。


# ONNX 导出、结构报告及 A4 部署

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [随机结构导出、来源SHA与报告](../functions/onnx-delivery.md)

上级：[挑战赛道](../modules/challenge.md)。

## 导出和报告

[export_onnx.py](../../../challenge/export/export_onnx.py) 用 StudentOnnxExportWrapper 将具名输出按 OUTPUT_NAMES 导出，opset 17、固定 batch 1，无 dynamic_axes；保存 model_id/config_id、source_git_sha、dataset_version、Schema 指纹和权重状态元数据。导出后同步写 model_structure.json 与 flops_report.json。[compute_flops.py](../../../challenge/export/compute_flops.py) 统计结构 FLOPs；[validate_artifacts.py](../../../challenge/export/validate_artifacts.py) 检查交付产物一致性。

当前 export_student_v0:38-48 只有 output、seed、source_git_sha，始终新建随机 Student；不能输入 A3 权重。它是结构 smoke 导出，PT 候选到部署 ONNX 尚缺接口。source_git_sha 参数只记录身份，不切换代码；复现需先切换相应代码版本。

## 部署功能

[horizon/README.md](../../../challenge/horizon/README.md) 描述 A4 工具链状态，[operator_mapping.md](../../../challenge/horizon/operator_mapping.md) 记录算子兼容性；[student_x86.py](../../../challenge/runtime/student_x86.py) 和 [x86_run.sh](../../../challenge/runtime/x86_run.sh) 在 ORT CPU 上做零输入 warmup/benchmark，生成 runtime_profile_x86.json。

该 X86 脚本只测模型前向，不接受 ModelRequest、不解码计划、不做 PlanValidator，不是生产 Planner Runtime；输入 Shape 目前独立硬编码在 student_x86.py:12-17，与 StudentShapeContract 存在将来漂移风险。J6P 编译格式、SDK 和板端运行尚待工具链确定，当前 X86 数值不能当板端性能结论。

## 验证与联动

[A1 测试](../../../challenge/tests/test_a1_student.py)、[交付测试](../../../challenge/tests/test_delivery.py) 与 validate_artifacts。运行重新导出会修改 ONNX 和报告，审核时优先验证现有产物，不无意覆盖当前版本。

修改模型或真实权重导出时同步 metadata、weights_status、dataset_version、config_id、结构状态、ONNX SHA、FLOPs 口径、ORT 一致性及 B3 产物身份；PyTorch 权重 SHA 与 ONNX SHA 必须分别保留。



## 模块接口与参数核对（2026-09-20）

export_student_v0输出ONNX及结构/FLOPs报告；StudentOnnxExportWrapper按OUTPUT_NAMES转tuple。当前出口新建随机模型，是结构smoke产物；没有接收A3训练权重的参数。

### 参数语义与生效边界

output为必填，seed默认20260911，source_git_sha=None由实现处理；传SHA只记录元数据，不切换代码。opset17、固定batch1。student_x86只测ORT前向，与完整ModelRequest→合法Plan的E2E不同。

### 上下游与修改影响

真实权重导出需联动权重来源、model/config、metadata、数值对齐和HIL身份；ONNX SHA不能替代源PT权重SHA，X86结果不能代替J6P性能。

### [challenge/export/export_onnx.py](../../../challenge/export/export_onnx.py) 的入口与声明

```python
StudentOnnxExportWrapper.__init__(self, model: StudentPlannerV0) -> None
StudentOnnxExportWrapper.forward(self, *inputs: torch.Tensor) -> tuple[torch.Tensor, ...]
export_student_v0(output: str | Path, *, seed: int=20260911, source_git_sha: str | None=None) -> Path
main() -> int
```

### [challenge/export/compute_flops.py](../../../challenge/export/compute_flops.py) 的入口与声明

```python
analyze_model() -> dict[str, Any]
main() -> int
```

### [challenge/runtime/student_x86.py](../../../challenge/runtime/student_x86.py) 的入口与声明

```python
build_inputs()
main()
```

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [challenge/export/__init__.py](../functions/challenge--export--__init__--py.md)
- [challenge/export/compute_flops.py](../functions/challenge--export--compute_flops--py.md)
- [challenge/export/export_onnx.py](../functions/challenge--export--export_onnx--py.md)
- [challenge/export/validate_artifacts.py](../functions/challenge--export--validate_artifacts--py.md)
- [challenge/runtime/student_x86.py](../functions/challenge--runtime--student_x86--py.md)
- [challenge/runtime/x86_run.sh](../functions/challenge--runtime--x86_run--sh.md)

## 诊断与维护交接

本模块证据：权重SHA、ONNX IO、数值对齐、编译配置；随机导出见AUDIT R01。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

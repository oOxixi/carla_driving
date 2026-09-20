# ONNX 导出、来源版本与产物一致性

上级：[导出与部署模块](../modules/challenge-export.md)。

## 当前可以做什么

[export_student_v0](../../../challenge/export/export_onnx.py) 设置随机种子，创建 StudentPlannerV0，使用零输入固定 Shape 导出 opset 17。wrapper 把 Python 具名字典转成 OUTPUT_NAMES 顺序的 tuple，避免 ONNX 输出位置漂移。

导出后写入 model_id、config_id、source_git_sha、seed、weights_status 与冻结契约指纹；再基于实际保存的 ONNX 更新 model_structure.json 和 flops_report.json。三个文件构成同一个结构交付。

## 不能误解的边界

- 当前没有 weights 参数，始终随机初始化。A3 训练权重还不能经该入口直接转成生产 ONNX。
- source_git_sha 默认当前 HEAD；显式传它只修改记录，不自动检出代码。产物提交的 HEAD 与真正生成它的代码提交可以不同。
- `student_v0_fp32.onnx` 文件名不编码训练状态，必须看 metadata/manifest。
- FLOPs 与模型文件大小、峰值运行内存、J6P 延时不是等价量。

## 产物校验覆盖与未覆盖

[validate_artifacts](../../../challenge/export/validate_artifacts.py) 检查冻结 Schema、ONNX hash、图合法性、输入 Shape、输出顺序、禁止动态算子、算子集合、身份与参数报告。A1 测试另比较 seeded PyTorch 和 ORT 输出。
这些不证明真实训练权重的精度、A4 编译成功或板端满足指标。

## 后续补训练权重导出时的联动

先确定 state_dict 与 model/config 的匹配和晋级清单，再加载权重、改变 weights_status/数据身份、导出与生成报告；数值比较要使用实际加载的权重而非重新 seed 的随机网络。最后对接 A4 输入和 B3 候选身份。此段是维护计划，没有在本轮实现。

验证入口：[test_delivery.py](../../../challenge/tests/test_delivery.py)、[test_a1_student.py](../../../challenge/tests/test_a1_student.py)。文档示例中的“重新导出”会改变产物，阅读文档本身无需执行它。

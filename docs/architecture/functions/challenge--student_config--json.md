# student_config：功能记录

上级模块：[模块说明](../modules/challenge-structure.md) · 实现：[challenge/student_config.json](../../../challenge/student_config.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [预处理真实变换与信息损失](student-preprocessing.md)

## 功能职责与范围

student_config

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `schema_version`：'1.0'。
- `model_id`：'student-v0-r3-fp32'。
- `config_id`：'student-v0-r3-structure-20260911'。
- `precision`：'fp32'。
- `batch`：1。
- `vision_channels`：列表，共 6 项。
- `encoder_width`：512。
- `fusion_widths`：列表，共 3 项。
- `max_steps`：4。
- `max_targets`：8。
- `max_target_speed_mps`：50.0。
- `initialization`：对象，直接字段：conv2d, linear, bias, export_seed。
- `onnx`：对象，直接字段：opset, dynamic_axes。
- `weights_status`：'random_initialization_for_export_smoke_only'。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-structure.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/student_config.json`

来源 SHA256：`15b1e72e233f195fde6809a015f2f1622133ded005c6b22801b8e032b422f15a`。

非Python/Schema资源：已核对内容指纹与来源存在性；参数生效和业务语义不能由指纹证明，参见所属模块与原资源记录。

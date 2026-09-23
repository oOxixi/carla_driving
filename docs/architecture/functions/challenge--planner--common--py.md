# common：功能记录

上级模块：[模块说明](../modules/challenge-planner.md) · 实现：[challenge/planner/common.py](../../../challenge/planner/common.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Head解码、约束修复和就绪判定](student-plan-decoding.md)

## 功能职责与范围

Shared request-to-scene projection for planner boundary validation.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `validation_scene`

源码位置：[challenge/planner/common.py 第 9 行](../../../challenge/planner/common.py#L9)。类型：`FunctionDef`。

```python
validation_scene(request: Mapping[str, Any]) -> dict[str, Any]
```

把 ModelRequest 的 scene summary、constraints、targets 和可选 capabilities 投影为 `PlanValidator` 场景。`objects` 只含 target_id/class/distance/confidence，`grounded_target_ids` 初值为所有 request targets；最后用 capabilities 顶层合并，因此 capability 中同名字段会覆盖初值。函数假定上游 Schema 已保证必填键。

## 内部调用与异常路径

- `validation_scene` 调用：`constraints.get`, `dict`, `request.get`, `scene.update`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py)
- [challenge/planner/teacher_backend.py](../../../challenge/planner/teacher_backend.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/planner/common.py`

来源 SHA256：`bc7c95bdf2adf8ebc244b9d0cf7d0cb44f3897b77aea6458a9bb5b0806b5c5e4`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

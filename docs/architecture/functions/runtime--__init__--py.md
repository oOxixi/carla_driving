# __init__：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[runtime/__init__.py](../../../runtime/__init__.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Role-A runtime infrastructure for the frozen second-group pipeline.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

## 内部调用与异常路径


显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [runtime/complexity_router.py](../../../runtime/complexity_router.py)
- [runtime/latency_trace.py](../../../runtime/latency_trace.py)
- [runtime/orchestrator.py](../../../runtime/orchestrator.py)
- [runtime/plan_compiler.py](../../../runtime/plan_compiler.py)
- [runtime/plan_validator.py](../../../runtime/plan_validator.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_qwen_planner_orchestrator.py](../../../integration/tests/test_qwen_planner_orchestrator.py)
- [integration/tests/test_role_a_orchestrator.py](../../../integration/tests/test_role_a_orchestrator.py)
- [integration/tests/test_second_group_runtime.py](../../../integration/tests/test_second_group_runtime.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-runtime---init---py"></a>

### `runtime/__init__.py`

来源 SHA256：`00089491d8ec8ec1dbff5c6581d32b7a41853f22020d4638ac8538e2dd48318f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

## 包导出边界（逐实现复核）

此文件重新导出 runtime 的编排、路由、计划校验/编译和延迟记录符号（InterfaceRegistry需从runtime.interface_registry导入），不提供另一套参数默认值。导入包不构造 PipelineOrchestrator；工作线程在编排器实例初始化时启动。修改导出名应检查 `from runtime import ...` 调用方；具体参数与副作用分别以本模块各实现页为准。

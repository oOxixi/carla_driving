# __init__：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/__init__.py](../../../car_control_D/__init__.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

__init__

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

- [car_control_D/control_runtime.py](../../../car_control_D/control_runtime.py)
- [car_control_D/execution_feedback.py](../../../car_control_D/execution_feedback.py)
- [car_control_D/official_score.py](../../../car_control_D/official_score.py)
- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)
- [car_control_D/schemas.py](../../../car_control_D/schemas.py)

静态 import 消费者（含测试）：

- [car_control_C/tests/test_strategy_generalization.py](../../../car_control_C/tests/test_strategy_generalization.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)
- [integration/scenario_runner_agent.py](../../../integration/scenario_runner_agent.py)
- [integration/tests/test_role_d_control_runtime.py](../../../integration/tests/test_role_d_control_runtime.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)
- [tools/validate_control_generalization.py](../../../tools/validate_control_generalization.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/__init__.py`

来源 SHA256：`f7bc3a027b564a43144011e19aec49943eeeabd170bc8ae0d8d24a5b2aafcc99`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

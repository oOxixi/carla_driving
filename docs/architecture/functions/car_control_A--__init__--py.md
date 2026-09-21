# __init__：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/__init__.py](../../../car_control_A/__init__.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

成员 A 的 CARLA 运行时边界包及其面向 C 的共享契约。

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

- [car_control_A/contracts.py](../../../car_control_A/contracts.py)
- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py)
- [car_control_A/simulator.py](../../../car_control_A/simulator.py)

静态 import 消费者（含测试）：

- [car_control_A/tests/test_ac_integration.py](../../../car_control_A/tests/test_ac_integration.py)
- [car_control_A/tests/test_contracts.py](../../../car_control_A/tests/test_contracts.py)
- [car_control_C/following_controller.py](../../../car_control_C/following_controller.py)
- [car_control_C/fuzzy_command_policy.py](../../../car_control_C/fuzzy_command_policy.py)
- [car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py)
- [car_control_C/safety_state.py](../../../car_control_C/safety_state.py)
- [car_control_C/speed_planner.py](../../../car_control_C/speed_planner.py)
- [car_control_C/tests/test_fuzzy_command_policy.py](../../../car_control_C/tests/test_fuzzy_command_policy.py)
- [car_control_C/tests/test_longitudinal.py](../../../car_control_C/tests/test_longitudinal.py)
- [car_control_C/tests/test_strategy_generalization.py](../../../car_control_C/tests/test_strategy_generalization.py)
- [car_control_C/traffic_rules.py](../../../car_control_C/traffic_rules.py)
- [car_control_D/benchmark.py](../../../car_control_D/benchmark.py)
- [integration/carla_perception.py](../../../integration/carla_perception.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/contracts.py](../../../integration/contracts.py)
- [integration/demo_offline.py](../../../integration/demo_offline.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/perception_bridge.py](../../../integration/perception_bridge.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)
- [integration/sensor_stability.py](../../../integration/sensor_stability.py)
- [integration/tests/test_carla_runner_helpers.py](../../../integration/tests/test_carla_runner_helpers.py)
- [integration/tests/test_perception_bridge.py](../../../integration/tests/test_perception_bridge.py)
- [integration/tests/test_runtime_loop.py](../../../integration/tests/test_runtime_loop.py)
- [integration/tests/test_scenario_evidence.py](../../../integration/tests/test_scenario_evidence.py)
- [integration/tests/test_voice_adapter.py](../../../integration/tests/test_voice_adapter.py)
- [integration/voice_adapter.py](../../../integration/voice_adapter.py)
- [tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)
- [tools/validate_c_role.py](../../../tools/validate_c_role.py)
- [tools/validate_control_generalization.py](../../../tools/validate_control_generalization.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-car-control-a---init---py"></a>

### `car_control_A/__init__.py`

来源 SHA256：`dd3f9ef4196584511464525d6dfa39d0507d900c371f973919fdb9f714646824`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

## 包导出与初始化副作用

导出A/C契约、HighLevelCommandAdapter及识别函数、ActorRegistry/CarlaSession/SensorFrameBuffer/SynchronousWorld；BehaviorFSM、ManeuverFSM、RuntimeWatchdog、LatencyTrace需从对应子模块导入。包导入不连接CARLA、不spawn/tick或启动线程；contracts会导入DEFAULT_STRATEGY，因此确认阈值来自配置加载而不是运行时每次查询。

# demo_offline：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/demo_offline.py](../../../integration/demo_offline.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

Offline acceptance demo: voice-envelope -> A/B/C/D -> final control.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-main"></a>

### `main`

源码位置：[integration/demo_offline.py 第 16 行](../../../integration/demo_offline.py#L16)。类型：`FunctionDef`。

```python
main() -> None
```

构造PurePursuit+ControlRuntime，提交18km/h的合法SET_SPEED envelope，以仿真0.05s、静止车辆、默认感知和世界x轴直线路线执行一帧dt=0.05s，打印final_control/safety_reason/safety_override。无CLI、CARLA或ASR模型调用；只做控制组合smoke，不验证模型推理和真实传感器。

## 内部调用与异常路径

- `main` 调用：`ControlRuntime`, `PerceptionFrame`, `PurePursuitController`, `RouteReference`, `RuntimeVehicleState`, `print`, `result.final_control.to_dict`, `runtime.step`, `runtime.submit_voice`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [integration/contracts.py](../../../integration/contracts.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-demo-offline-py"></a>

### `integration/demo_offline.py`

来源 SHA256：`291f48534bba2c87df103e37af455c1891ccc738f744f04ad68fd5986f7e7362`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

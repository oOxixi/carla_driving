# validation：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/validation.py](../../../car_control_C/validation.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

Strict numeric validation shared by C's public control APIs.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `finite`

源码位置：[car_control_C/validation.py 第 8 行](../../../car_control_C/validation.py#L8)。类型：`FunctionDef`。

```python
finite(name: str, value: object, *, minimum: float | None=None, maximum: float | None=None, positive: bool=False) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `finite` 调用：`TypeError`, `ValueError`, `float`, `math.isfinite`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `finite`，第 11 行：`TypeError(f'{name} must be an int or float, not {type(value).__name__}')`。
- `finite`，第 14 行：`ValueError(f'{name} must be finite')`。
- `finite`，第 16 行：`ValueError(f'{name} must be positive')`。
- `finite`，第 18 行：`ValueError(f'{name} must be >= {minimum}')`。
- `finite`，第 20 行：`ValueError(f'{name} must be <= {maximum}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_C/following_controller.py](../../../car_control_C/following_controller.py)
- [car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py)
- [car_control_C/safety_state.py](../../../car_control_C/safety_state.py)
- [car_control_C/speed_pid.py](../../../car_control_C/speed_pid.py)
- [car_control_C/speed_planner.py](../../../car_control_C/speed_planner.py)
- [car_control_C/stop_controller.py](../../../car_control_C/stop_controller.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/validation.py`

来源 SHA256：`481fe98716e701f177cbfac8c948269eac6f349206a1c6cbeb8010d8cbb7ac18`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `finite` / 11 | `type(value) not in (int, float)` | `raise TypeError(f'{name} must be an int or float, not {type(value).__name__}')` |
| `finite` / 14 | `not math.isfinite(result)` | `raise ValueError(f'{name} must be finite')` |
| `finite` / 16 | `positive and result <= 0.0` | `raise ValueError(f'{name} must be positive')` |
| `finite` / 18 | `minimum is not None and result < minimum` | `raise ValueError(f'{name} must be >= {minimum}')` |
| `finite` / 20 | `maximum is not None and result > maximum` | `raise ValueError(f'{name} must be <= {maximum}')` |

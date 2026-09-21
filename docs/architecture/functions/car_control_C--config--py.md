# config：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/config.py](../../../car_control_C/config.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

Strict, serialisable configuration for C's local command safety policy.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `FuzzyCommandPolicyConfig.confidence_threshold: float`；默认：`DEFAULT_STRATEGY.common.command_confidence_threshold`。
- `FuzzyCommandPolicyConfig.comfort_decel_mps2: float`；默认：`DEFAULT_STRATEGY.common.comfortable_decel_mps2`。
- `FuzzyCommandPolicyConfig.max_decel_mps2: float`；默认：`DEFAULT_STRATEGY.common.max_decel_mps2`。
- `FuzzyCommandPolicyConfig.hold_brake: float`；默认：`DEFAULT_STRATEGY.common.hold_brake`。
- `FuzzyCommandPolicyConfig.emergency_brake: float`；默认：`DEFAULT_STRATEGY.common.emergency_brake`。
- `FuzzyCommandPolicyConfig.standstill_speed_mps: float`；默认：`DEFAULT_STRATEGY.common.standstill_speed_mps`。

## 功能入口：输入、输出与实现说明

### `_finite`

源码位置：[car_control_C/config.py 第 13 行](../../../car_control_C/config.py#L13)。类型：`FunctionDef`。

```python
_finite(name: str, value: object, *, minimum: float | None=None, maximum: float | None=None, positive: bool=False) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FuzzyCommandPolicyConfig`

源码位置：[car_control_C/config.py 第 30 行](../../../car_control_C/config.py#L30)。类型：`ClassDef`。

SI-only policy parameters; D remains the final safety authority.

### `FuzzyCommandPolicyConfig.__post_init__`

源码位置：[car_control_C/config.py 第 40 行](../../../car_control_C/config.py#L40)。类型：`FunctionDef`。

```python
FuzzyCommandPolicyConfig.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FuzzyCommandPolicyConfig.to_dict`

源码位置：[car_control_C/config.py 第 56 行](../../../car_control_C/config.py#L56)。类型：`FunctionDef`。

```python
FuzzyCommandPolicyConfig.to_dict(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FuzzyCommandPolicyConfig.from_dict`

源码位置：[car_control_C/config.py 第 60 行](../../../car_control_C/config.py#L60)。类型：`FunctionDef`。

```python
FuzzyCommandPolicyConfig.from_dict(cls, payload: object) -> 'FuzzyCommandPolicyConfig'
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_finite` 调用：`TypeError`, `ValueError`, `float`, `math.isfinite`, `type`.
- `__post_init__` 调用：`ValueError`, `_finite`, `object.__setattr__`.
- `to_dict` 调用：`asdict`.
- `from_dict` 调用：`TypeError`, `ValueError`, `cls`, `set`, `sorted`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 48 行：`ValueError('comfort_decel_mps2 must not exceed max_decel_mps2')`。
- `_finite`，第 16 行：`TypeError(f'{name} must be an int or float, not {type(value).__name__}')`。
- `_finite`，第 19 行：`ValueError(f'{name} must be finite')`。
- `_finite`，第 21 行：`ValueError(f'{name} must be positive')`。
- `_finite`，第 23 行：`ValueError(f'{name} must be >= {minimum}')`。
- `_finite`，第 25 行：`ValueError(f'{name} must be <= {maximum}')`。
- `from_dict`，第 62 行：`TypeError('payload must be a plain dict')`。
- `from_dict`，第 67 行：`ValueError(f'payload fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}')`。
- `from_dict`，第 69 行：`ValueError('unsupported schema_version')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [car_control_C/fuzzy_command_policy.py](../../../car_control_C/fuzzy_command_policy.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/config.py`

来源 SHA256：`1a7dea242958860fcbdbb641dea1d2f9321202bc4e0a509a97ac7294fff4b956`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `FuzzyCommandPolicyConfig.confidence_threshold` | `float` | `DEFAULT_STRATEGY.common.command_confidence_threshold` |
| `FuzzyCommandPolicyConfig.comfort_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.comfortable_decel_mps2` |
| `FuzzyCommandPolicyConfig.max_decel_mps2` | `float` | `DEFAULT_STRATEGY.common.max_decel_mps2` |
| `FuzzyCommandPolicyConfig.hold_brake` | `float` | `DEFAULT_STRATEGY.common.hold_brake` |
| `FuzzyCommandPolicyConfig.emergency_brake` | `float` | `DEFAULT_STRATEGY.common.emergency_brake` |
| `FuzzyCommandPolicyConfig.standstill_speed_mps` | `float` | `DEFAULT_STRATEGY.common.standstill_speed_mps` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_finite` / 16 | `type(value) not in (int, float)` | `raise TypeError(f'{name} must be an int or float, not {type(value).__name__}')` |
| `_finite` / 19 | `not math.isfinite(number)` | `raise ValueError(f'{name} must be finite')` |
| `_finite` / 21 | `positive and number <= 0.0` | `raise ValueError(f'{name} must be positive')` |
| `_finite` / 23 | `minimum is not None and number < minimum` | `raise ValueError(f'{name} must be >= {minimum}')` |
| `_finite` / 25 | `maximum is not None and number > maximum` | `raise ValueError(f'{name} must be <= {maximum}')` |
| `FuzzyCommandPolicyConfig.__post_init__` / 48 | `self.comfort_decel_mps2 > self.max_decel_mps2` | `raise ValueError('comfort_decel_mps2 must not exceed max_decel_mps2')` |
| `FuzzyCommandPolicyConfig.from_dict` / 62 | `type(payload) is not dict` | `raise TypeError('payload must be a plain dict')` |
| `FuzzyCommandPolicyConfig.from_dict` / 67 | `set(payload) != fields` | `raise ValueError(f'payload fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}')` |
| `FuzzyCommandPolicyConfig.from_dict` / 69 | `payload['schema_version'] != CONFIG_SCHEMA_VERSION` | `raise ValueError('unsupported schema_version')` |

### car_control_C/config.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 41 | `_finite('confidence_threshold', self.confidence_threshold, minimum=0.0, maximum=1.0)` |
| 43 | `_finite('comfort_decel_mps2', self.comfort_decel_mps2, positive=True)` |
| 45 | `_finite('max_decel_mps2', self.max_decel_mps2, positive=True)` |
| 49 | `_finite('hold_brake', self.hold_brake, positive=True, maximum=1.0)` |
| 51 | `_finite('emergency_brake', self.emergency_brake, positive=True, maximum=1.0)` |
| 53 | `_finite('standstill_speed_mps', self.standstill_speed_mps, minimum=0.0)` |

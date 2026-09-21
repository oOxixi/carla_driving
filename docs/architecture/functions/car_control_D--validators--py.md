# validators：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/validators.py](../../../car_control_D/validators.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

Validation rules for commands, controls and final feedback.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_finite_number`

源码位置：[car_control_D/validators.py 第 11 行](../../../car_control_D/validators.py#L11)。类型：`FunctionDef`。

```python
_finite_number(name: str, value: float, errors: List[str]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_control`

源码位置：[car_control_D/validators.py 第 16 行](../../../car_control_D/validators.py#L16)。类型：`FunctionDef`。

```python
validate_control(control: Any) -> ValidationResult
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_command`

源码位置：[car_control_D/validators.py 第 37 行](../../../car_control_D/validators.py#L37)。类型：`FunctionDef`。

```python
validate_command(command: Any) -> ValidationResult
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_execution_feedback`

源码位置：[car_control_D/validators.py 第 70 行](../../../car_control_D/validators.py#L70)。类型：`FunctionDef`。

```python
validate_execution_feedback(feedback: Any) -> ValidationResult
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_finite_number` 调用：`errors.append`, `float`, `isinstance`, `math.isfinite`.
- `validate_control` 调用：`ValidationResult`, `_finite_number`, `adapt_control`, `errors.append`, `len`.
- `validate_command` 调用：`ValidationResult`, `adapt_command`, `cmd.parameters.get`, `errors.append`, `len`, `str`, `str(cmd.parameters.get('direction', '')).upper`, `warnings.append`.
- `validate_execution_feedback` 调用：`ValidationResult`, `errors.append`, `feedback.get`, `getattr`, `isinstance`, `len`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_D/adapters.py](../../../car_control_D/adapters.py)
- [car_control_D/schemas.py](../../../car_control_D/schemas.py)

静态 import 消费者（含测试）：

- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)
- [car_control_D/tests/test_validators.py](../../../car_control_D/tests/test_validators.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/validators.py`

来源 SHA256：`007b928e235616ba5b9d4522d0ac2a3934df7f962c3cfb708467664c4d8f2975`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

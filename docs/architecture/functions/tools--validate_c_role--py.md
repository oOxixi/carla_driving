# validate_c_role：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/validate_c_role.py](../../../tools/validate_c_role.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Generate member C's deterministic pre-CARLA acceptance evidence.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_write_csv`

源码位置：[tools/validate_c_role.py 第 34 行](../../../tools/validate_c_role.py#L34)。类型：`FunctionDef`。

```python
_write_csv(path: Path, rows: list[dict[str, object]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_distance_ttc_samples`

源码位置：[tools/validate_c_role.py 第 43 行](../../../tools/validate_c_role.py#L43)。类型：`FunctionDef`。

```python
_distance_ttc_samples() -> list[dict[str, object]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_voice_stop`

源码位置：[tools/validate_c_role.py 第 82 行](../../../tools/validate_c_role.py#L82)。类型：`FunctionDef`。

```python
_voice_stop() -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_stop_curve`

源码位置：[tools/validate_c_role.py 第 101 行](../../../tools/validate_c_role.py#L101)。类型：`FunctionDef`。

```python
_stop_curve() -> list[dict[str, object]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_fault_injection`

源码位置：[tools/validate_c_role.py 第 139 行](../../../tools/validate_c_role.py#L139)。类型：`FunctionDef`。

```python
_fault_injection() -> list[dict[str, object]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate`

源码位置：[tools/validate_c_role.py 第 184 行](../../../tools/validate_c_role.py#L184)。类型：`FunctionDef`。

```python
validate(output_dir: Path) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/validate_c_role.py 第 247 行](../../../tools/validate_c_role.py#L247)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_write_csv` 调用：`ValueError`, `csv.DictWriter`, `list`, `path.open`, `writer.writeheader`, `writer.writerows`.
- `_distance_ttc_samples` 调用：`ConservativeSensorFusion`, `VisualObservation`, `fusion.update`, `rows.append`.
- `_stop_curve` 调用：`ControlRuntime`, `PerceptionFrame`, `PurePursuitController`, `RouteReference`, `RuntimeVehicleState`, `_voice_stop`, `float`, `max`, `range`, `round`, `rows.append`, `runtime.step`, `runtime.submit_voice`.
- `_fault_injection` 调用：`ConservativeSensorFusion`, `VisualObservation`, `VisualObservation.unavailable`, `fusion.fail_closed_control`, `fusion.reset`, `fusion.update`.
- `validate` 调用：`(output_dir / 'fault_injection.json').write_text`, `(output_dir / 'summary.json').write_text`, `LongitudinalParameters`, `SafetyStateParameters`, `_distance_ttc_samples`, `_fault_injection`, `_stop_curve`, `_write_csv`, `all`, `any`, `asdict`, `bool`, `checks.values`, `float`, `json.dumps`, `len`, `min`, `output_dir.mkdir`.
- `main` 调用：`argparse.ArgumentParser`, `args.output_dir.resolve`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `validate`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_write_csv`，第 36 行：`ValueError('CSV evidence must contain at least one row')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 249 行：`parser.add_argument('--output-dir', type=Path, default=REPOSITORY_ROOT / 'artifacts' / 'C_role_validation')`。

## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [integration/__init__.py](../../../integration/__init__.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/validate_c_role.py`

来源 SHA256：`1334795803be3ba1f2c59eda58dc637410d0cbaea4aac03273f1c7e73ee0b099`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 249 | `'--output-dir'` | `type=Path; default=REPOSITORY_ROOT / 'artifacts' / 'C_role_validation'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_write_csv` / 36 | `not rows` | `raise ValueError('CSV evidence must contain at least one row')` |

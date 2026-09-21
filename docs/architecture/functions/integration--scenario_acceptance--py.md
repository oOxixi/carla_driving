# scenario_acceptance：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/scenario_acceptance.py](../../../integration/scenario_acceptance.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

Strict evaluation of scenario ``expected`` contracts.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_number`

源码位置：[integration/scenario_acceptance.py 第 13 行](../../../integration/scenario_acceptance.py#L13)。类型：`FunctionDef`。

```python
_number(value: object) -> float | None
```

仅接受精确 int/float 且非 bool，转换为有限 float；类型不符或 NaN/Inf 返回 `None` 而非抛错。数值范围和单位由各具体验收项决定。

### `evaluate_expected`

源码位置：[integration/scenario_acceptance.py 第 20 行](../../../integration/scenario_acceptance.py#L20)。类型：`FunctionDef`。

```python
evaluate_expected(expected: Mapping[str, object], metrics: Mapping[str, object]) -> dict[str, Any]
```

逐键把场景 `expected` 与 recorder/scoring context 的 metrics 比较，返回总 passed、每项 PASS/FAIL、failed_keys、unsupported_keys 和数量。支持启动/调用/路线/命令布尔项、误差/速度/间距阈值、安全事件、重规划、停止线及目标速度等；未知 key 必定失败关闭。函数信任 metrics 的来源，合同通过不等于这些值来自真实传感器或冻结运行。

### `evaluate_expected.add`

源码位置：[integration/scenario_acceptance.py 第 23 行](../../../integration/scenario_acceptance.py#L23)。类型：`FunctionDef`。

```python
evaluate_expected.add(key: str, passed: bool, actual: object, required: object, detail: str) -> None
```

向 checks 追加统一记录，status 只由传入 passed 转为 PASS/FAIL，并原样保存 actual、required、detail。闭包不去重，同一语义可因两个 expected key 生成两条检查。

### `evaluate_expected.maximum`

源码位置：[integration/scenario_acceptance.py 第 32 行](../../../integration/scenario_acceptance.py#L32)。类型：`FunctionDef`。

```python
evaluate_expected.maximum(key: str, metric: str) -> None
```

把 metrics 指定值和 expected 当前 key 都经 `_number`，两者有效且 actual≤required 才通过；缺测、非法或 NaN 均失败，并在记录中保留转换后的 `None`。

### `evaluate_expected.minimum`

源码位置：[integration/scenario_acceptance.py 第 37 行](../../../integration/scenario_acceptance.py#L37)。类型：`FunctionDef`。

```python
evaluate_expected.minimum(key: str, metric: str) -> None
```

与 maximum 对称，要求两个有限数存在且 actual≥required；用于最小前距、最短运行时间等下界合同，不自行解释单位。

## 内部调用与异常路径

- `_number` 调用：`float`, `isinstance`, `math.isfinite`, `type`.
- `evaluate_expected` 调用：`' '.join`, `' '.join(reasons).lower`, `_number`, `abs`, `add`, `any`, `bool`, `bool_metrics.items`, `checks.append`, `expected.get`, `float`, `int`, `isinstance`, `len`, `max_metrics.items`, `maximum`, `metrics.get`, `min_metrics.items`, `minimum`, `required.issubset`, `set`, `simple_no_event.items`, `sorted`, `str`, `str(expected['turn_direction']).upper`, `str(item).lower`, `str(item).strip`, `str(item).strip().lower`, `str(metrics.get('turn_direction', 'UNKNOWN')).upper`, `supported.add`.
- `add` 调用：`checks.append`.
- `maximum` 调用：`_number`, `add`, `metrics.get`.
- `minimum` 调用：`_number`, `add`, `metrics.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/scenario_evidence.py](../../../integration/scenario_evidence.py)
- [integration/tests/test_acceptance_suite_contracts.py](../../../integration/tests/test_acceptance_suite_contracts.py)
- [integration/tests/test_scenario_acceptance.py](../../../integration/tests/test_scenario_acceptance.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/scenario_acceptance.py`

来源 SHA256：`06794959dbb83a7ee0097dd0d7fec2c3b6516e065224b046fb5123f6467af564`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

### integration/scenario_acceptance.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 168 | `_number(metrics.get('configured_route_deviation_trigger_m'))` |
| 169 | `_number(expected['route_deviation_trigger_m'])` |
| 246 | `_number(metrics.get('final_speed_mps'))` |
| 264 | `_number(metrics.get('speed_before_decrease_marker_mps'))` |
| 265 | `_number(metrics.get('speed_after_decrease_marker_mps'))` |
| 33 | `_number(metrics.get(metric))` |
| 33 | `_number(expected[key])` |
| 38 | `_number(metrics.get(metric))` |
| 38 | `_number(expected[key])` |
| 102 | `_number(metrics.get('initial_cross_track_error_m'))` |
| 102 | `_number(expected['initial_offset_y_m'])` |
| 108 | `_number(metrics.get('final_lateral_shift_m'))` |
| 108 | `_number(expected['final_lateral_shift_m'])` |
| 235 | `_number(metrics.get('final_speed_mps'))` |

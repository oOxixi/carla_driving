# official_score：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/official_score.py](../../../car_control_D/official_score.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

Scoring utilities for D. Implements baseline 25/10/5 penalties and summaries.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ScoreBreakdown.scenario_id: str`；默认：`未在声明处设置`。
- `ScoreBreakdown.difficulty: str`；默认：`未在声明处设置`。
- `ScoreBreakdown.base_score: float`；默认：`未在声明处设置`。
- `ScoreBreakdown.deduction: float`；默认：`未在声明处设置`。
- `ScoreBreakdown.final_score: float`；默认：`未在声明处设置`。
- `ScoreBreakdown.serious_safety_events: int`；默认：`0`。
- `ScoreBreakdown.serious_route_deviation: int`；默认：`0`。
- `ScoreBreakdown.unfinished_tasks: int`；默认：`0`。

## 功能入口：输入、输出与实现说明

### `ScoreBreakdown`

源码位置：[car_control_D/official_score.py 第 10 行](../../../car_control_D/official_score.py#L10)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScoreBreakdown.to_dict`

源码位置：[car_control_D/official_score.py 第 20 行](../../../car_control_D/official_score.py#L20)。类型：`FunctionDef`。

```python
ScoreBreakdown.to_dict(self) -> Dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `calculate_deduction`

源码位置：[car_control_D/official_score.py 第 24 行](../../../car_control_D/official_score.py#L24)。类型：`FunctionDef`。

```python
calculate_deduction(result: Dict[str, Any]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `score_scenario`

源码位置：[car_control_D/official_score.py 第 36 行](../../../car_control_D/official_score.py#L36)。类型：`FunctionDef`。

```python
score_scenario(result: Dict[str, Any], base_score: float=25.0) -> ScoreBreakdown
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `weighted_completion_score`

源码位置：[car_control_D/official_score.py 第 51 行](../../../car_control_D/official_score.py#L51)。类型：`FunctionDef`。

```python
weighted_completion_score(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `latency_report`

源码位置：[car_control_D/official_score.py 第 69 行](../../../car_control_D/official_score.py#L69)。类型：`FunctionDef`。

```python
latency_report(command_records: Iterable[Dict[str, Any]]) -> Dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OfficialScorer`

源码位置：[car_control_D/official_score.py 第 92 行](../../../car_control_D/official_score.py#L92)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OfficialScorer.score_scenario`

源码位置：[car_control_D/official_score.py 第 93 行](../../../car_control_D/official_score.py#L93)。类型：`FunctionDef`。

```python
OfficialScorer.score_scenario(self, result: Dict[str, Any], base_score: float=25.0) -> ScoreBreakdown
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OfficialScorer.summarize`

源码位置：[car_control_D/official_score.py 第 96 行](../../../car_control_D/official_score.py#L96)。类型：`FunctionDef`。

```python
OfficialScorer.summarize(self, scenario_results: Iterable[Dict[str, Any]], command_records: Optional[Iterable[Dict[str, Any]]]=None) -> Dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `calculate_deduction` 调用：`float`, `int`, `result.get`.
- `score_scenario` 调用：`ScoreBreakdown`, `calculate_deduction`, `float`, `int`, `max`, `result.get`, `score_scenario`, `str`.
- `weighted_completion_score` 调用：`buckets.items`, `buckets[diff].append`, `mean`, `r.get`, `str`, `str(r.get('difficulty', r.get('difficulty_level', 'basic'))).lower`, `str(r.get('status', 'FAILED')).upper`.
- `latency_report` 调用：`asr_latencies.append`, `c.get`, `float`, `intent_latencies.append`, `isinstance`, `latencies.append`, `len`, `max`, `mean`, `sum`.
- `to_dict` 调用：`asdict`.
- `summarize` 调用：`latency_report`, `list`, `score_scenario`, `score_scenario(r).to_dict`, `weighted_completion_score`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [car_control_D/metrics.py](../../../car_control_D/metrics.py)
- [car_control_D/scenario_runner.py](../../../car_control_D/scenario_runner.py)
- [car_control_D/tests/test_official_score.py](../../../car_control_D/tests/test_official_score.py)
- [integration/scenario_evidence.py](../../../integration/scenario_evidence.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/official_score.py`

来源 SHA256：`34d8c1c52d88cc0f8773f07ddd88d10f2608ff9cd17501b84529e90250ad99f4`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ScoreBreakdown.scenario_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ScoreBreakdown.difficulty` | `str` | `无声明默认；构造/赋值方提供` |
| `ScoreBreakdown.base_score` | `float` | `无声明默认；构造/赋值方提供` |
| `ScoreBreakdown.deduction` | `float` | `无声明默认；构造/赋值方提供` |
| `ScoreBreakdown.final_score` | `float` | `无声明默认；构造/赋值方提供` |
| `ScoreBreakdown.serious_safety_events` | `int` | `0` |
| `ScoreBreakdown.serious_route_deviation` | `int` | `0` |
| `ScoreBreakdown.unfinished_tasks` | `int` | `0` |

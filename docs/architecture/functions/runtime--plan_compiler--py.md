# plan_compiler：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[runtime/plan_compiler.py](../../../runtime/plan_compiler.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Compile validated ManeuverPlan V2 payloads into deterministic FSM steps.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `CompiledPlanStep.step_id: str`；默认：`未在声明处设置`。
- `CompiledPlanStep.source_step_id: str`；默认：`未在声明处设置`。
- `CompiledPlanStep.behavior: str`；默认：`未在声明处设置`。
- `CompiledPlanStep.target: Mapping[str, Any]`；默认：`未在声明处设置`。
- `CompiledPlanStep.preconditions: tuple[str, ...]`；默认：`未在声明处设置`。
- `CompiledPlanStep.completion: Mapping[str, Any]`；默认：`未在声明处设置`。
- `CompiledPlanStep.timeout_s: float`；默认：`未在声明处设置`。
- `CompiledPlanStep.on_failure: str`；默认：`未在声明处设置`。
- `CompiledManeuverPlan.command_id: str`；默认：`未在声明处设置`。
- `CompiledManeuverPlan.plan_id: str`；默认：`未在声明处设置`。
- `CompiledManeuverPlan.steps: tuple[CompiledPlanStep, ...]`；默认：`未在声明处设置`。
- `CompiledManeuverPlan.replan_conditions: tuple[str, ...]`；默认：`未在声明处设置`。
- `CompiledManeuverPlan.valid_until_ns: int`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-compiledplanstep"></a>

### `CompiledPlanStep`

源码位置：[runtime/plan_compiler.py 第 11 行](../../../runtime/plan_compiler.py#L11)。类型：`ClassDef`。

内部执行步骤，step_id可带展开后缀，source_step_id保留模型原步身份；target/completion为mapping，冻结dataclass不保证内部映射不可变。

<a id="fn-compiledplanstep-to-dict"></a>

### `CompiledPlanStep.to_dict`

源码位置：[runtime/plan_compiler.py 第 21 行](../../../runtime/plan_compiler.py#L21)。类型：`FunctionDef`。

```python
CompiledPlanStep.to_dict(self) -> dict[str, Any]
```

asdict后显式将target/completion转dict、preconditions转list，适合记录/交给FSM；不是Schema验证。

<a id="fn-compiledmaneuverplan"></a>

### `CompiledManeuverPlan`

源码位置：[runtime/plan_compiler.py 第 30 行](../../../runtime/plan_compiler.py#L30)。类型：`ClassDef`。

聚合command/plan身份、内部steps、replan_conditions和valid_until_ns；内部步数可超过模型Schema的4步。

<a id="fn-compiledmaneuverplan-to-dict"></a>

### `CompiledManeuverPlan.to_dict`

源码位置：[runtime/plan_compiler.py 第 37 行](../../../runtime/plan_compiler.py#L37)。类型：`FunctionDef`。

```python
CompiledManeuverPlan.to_dict(self) -> dict[str, Any]
```

序列化每个step并将tuple转list，保持command/plan和有效期，不生成request_id或控制量。

<a id="fn-plancompiler"></a>

### `PlanCompiler`

源码位置：[runtime/plan_compiler.py 第 47 行](../../../runtime/plan_compiler.py#L47)。类型：`ClassDef`。

Expand semantic maneuvers without producing throttle/brake/steer.

<a id="fn-plancompiler-compile"></a>

### `PlanCompiler.compile`

源码位置：[runtime/plan_compiler.py 第 50 行](../../../runtime/plan_compiler.py#L50)。类型：`FunctionDef`。

```python
PlanCompiler.compile(self, plan: Mapping[str, Any], *, scene: Mapping[str, Any] | None=None) -> CompiledManeuverPlan
```

输入plan/context须Mapping，按顺序展开避障、返回、变道，其余复制。避障后记相反方向供下一RETURN使用，返回后清除该方向。空结果ValueError；前置假设是已验证计划，本函数不重跑Schema。

<a id="fn-plancompiler--compile-change-lane"></a>

### `PlanCompiler._compile_change_lane`

源码位置：[runtime/plan_compiler.py 第 95 行](../../../runtime/plan_compiler.py#L95)。类型：`FunctionDef`。

```python
PlanCompiler._compile_change_lane(raw: Mapping[str, Any]) -> tuple[CompiledPlanStep, ...]
```

Gate every ordinary lane change on a fresh, safe target-lane gap.

按LEFT/RIGHT行为强制target_lane为相应ADJACENT；将PERCEPTION_FRESH、该侧LANE_EXISTS/GAP_SAFE追加到原preconditions并保序去重。普通变道仍编译为一个步骤，step_id/source_step_id相同，completion/timeout_s/on_failure保留。

<a id="fn-plancompiler--compile-avoid"></a>

### `PlanCompiler._compile_avoid`

源码位置：[runtime/plan_compiler.py 第 119 行](../../../runtime/plan_compiler.py#L119)。类型：`FunctionDef`。

```python
PlanCompiler._compile_avoid(raw: Mapping[str, Any], scene: Mapping[str, Any]) -> tuple[CompiledPlanStep, ...]
```

目标邻道未指明时优先已知左道再右道，无则ValueError。缺速度默认3m/s；展开slow/gap/lane/pass，前两步timeout=min(5,原timeout)，后两步原timeout；hold_frames依次3/3/8/3，slow完成速度为目标+0.3。保留source_step和on_failure。

<a id="fn-plancompiler--compile-return"></a>

### `PlanCompiler._compile_return`

源码位置：[runtime/plan_compiler.py 第 170 行](../../../runtime/plan_compiler.py#L170)。类型：`FunctionDef`。

```python
PlanCompiler._compile_return(raw: Mapping[str, Any], scene: Mapping[str, Any]) -> tuple[CompiledPlanStep, CompiledPlanStep]
```

优先scene.return_direction，否则由当前LEFT/RIGHT_ADJACENT与原CURRENT推导反向；不确定则拒绝。展开WAIT_SAFE_GAP（最多8s、3帧）及返回变道；移动步去掉相对邻道exists/gap条件，避免目标道变为CURRENT后无法完成。

<a id="fn--copy-step"></a>

### `_copy_step`

源码位置：[runtime/plan_compiler.py 第 223 行](../../../runtime/plan_compiler.py#L223)。类型：`FunctionDef`。

```python
_copy_step(raw: Mapping[str, Any]) -> CompiledPlanStep
```

浅层规范化原步字段为str/dict/tuple/float，step_id同时作source_step_id，原completion/timeout/on_failure保留；不会检查可行性。

## 内部调用与异常路径

- `_copy_step` 调用：`CompiledPlanStep`, `dict`, `float`, `str`, `tuple`.
- `to_dict` 调用：`asdict`, `dict`, `list`, `step.to_dict`.
- `compile` 调用：`CompiledManeuverPlan`, `TypeError`, `ValueError`, `_copy_step`, `avoid_steps[-1].target.get`, `compiled.append`, `compiled.extend`, `dict`, `int`, `isinstance`, `self._compile_avoid`, `self._compile_change_lane`, `self._compile_return`, `str`, `tuple`.
- `_compile_change_lane` 调用：`CompiledPlanStep`, `dict`, `dict.fromkeys`, `float`, `str`, `tuple`.
- `_compile_avoid` 调用：`CompiledPlanStep`, `ValueError`, `bool`, `dict`, `dict.fromkeys`, `float`, `min`, `scene.get`, `str`, `target.get`, `tuple`.
- `_compile_return` 调用：`CompiledPlanStep`, `ValueError`, `dict`, `dict.fromkeys`, `float`, `int`, `min`, `scene.get`, `str`, `str(scene.get('current_lane', '')).upper`, `str(scene.get('original_lane', '')).upper`, `str(scene.get('return_direction', '')).upper`, `tuple`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_compile_avoid`，第 130 行：`ValueError('AVOID_OBSTACLE requires a verified adjacent target lane')`。
- `_compile_return`，第 182 行：`ValueError('RETURN_TO_LANE requires deterministic return_direction')`。
- `compile`，第 57 行：`TypeError('plan must be a mapping')`。
- `compile`，第 60 行：`TypeError('scene must be a mapping or None')`。
- `compile`，第 85 行：`ValueError('compiled plan must contain at least one step')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_A/maneuver_fsm.py](../../../car_control_A/maneuver_fsm.py)
- [car_control_A/tests/test_maneuver_fsm.py](../../../car_control_A/tests/test_maneuver_fsm.py)
- [integration/qwen_plan_adapter.py](../../../integration/qwen_plan_adapter.py)
- [integration/tests/test_plan_compiler.py](../../../integration/tests/test_plan_compiler.py)
- [runtime/__init__.py](../../../runtime/__init__.py)
- [runtime/orchestrator.py](../../../runtime/orchestrator.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-runtime-plan-compiler-py"></a>

### `runtime/plan_compiler.py`

来源 SHA256：`4ee22cfd30a6b6bf9cdcf2bb899d76e6d4c7f64c81fac9b8349df0fec02aa16b`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `CompiledPlanStep.step_id` | `str` | `无声明默认；构造/赋值方提供` |
| `CompiledPlanStep.source_step_id` | `str` | `无声明默认；构造/赋值方提供` |
| `CompiledPlanStep.behavior` | `str` | `无声明默认；构造/赋值方提供` |
| `CompiledPlanStep.target` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `CompiledPlanStep.preconditions` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `CompiledPlanStep.completion` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `CompiledPlanStep.timeout_s` | `float` | `无声明默认；构造/赋值方提供` |
| `CompiledPlanStep.on_failure` | `str` | `无声明默认；构造/赋值方提供` |
| `CompiledManeuverPlan.command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `CompiledManeuverPlan.plan_id` | `str` | `无声明默认；构造/赋值方提供` |
| `CompiledManeuverPlan.steps` | `tuple[CompiledPlanStep, ...]` | `无声明默认；构造/赋值方提供` |
| `CompiledManeuverPlan.replan_conditions` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `CompiledManeuverPlan.valid_until_ns` | `int` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `PlanCompiler.compile` / 57 | `not isinstance(plan, Mapping)` | `raise TypeError('plan must be a mapping')` |
| `PlanCompiler.compile` / 60 | `not isinstance(context, Mapping)` | `raise TypeError('scene must be a mapping or None')` |
| `PlanCompiler.compile` / 85 | `not compiled` | `raise ValueError('compiled plan must contain at least one step')` |
| `PlanCompiler._compile_avoid` / 130 | `lane not in {'LEFT_ADJACENT', 'RIGHT_ADJACENT'} AND NOT (bool(scene.get('left_lane_exists', False))) AND NOT (bool(scene.get('right_lane_exists', False)))` | `raise ValueError('AVOID_OBSTACLE requires a verified adjacent target lane')` |
| `PlanCompiler._compile_return` / 182 | `direction not in {'LEFT', 'RIGHT'} AND NOT (current_lane == 'LEFT_ADJACENT' and original_lane == 'CURRENT') AND NOT (current_lane == 'RIGHT_ADJACENT' and original_lane == 'CURRENT')` | `raise ValueError('RETURN_TO_LANE requires deterministic return_direction')` |

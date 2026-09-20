# canonical_bridge：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/canonical_bridge.py](../../../integration/canonical_bridge.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Adapters between the legacy CARLA loop and frozen second-group V1 objects.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-voice-envelope-to-driving-command"></a>

### `voice_envelope_to_driving_command`

源码位置：[integration/canonical_bridge.py 第 27 行](../../../integration/canonical_bridge.py#L27)。类型：`FunctionDef`。

```python
voice_envelope_to_driving_command(envelope: Mapping[str, Any], *, received_at_ns: int, registry: InterfaceRegistry | None=None) -> dict[str, Any]
```

intent映射保留FOLLOW，HOLD映STOP，左右动作合并intent加direction。优先合法target_speed_mps，否则legacy speed默认km/h换算；未知unit当前落入原数值分支，不能说严格拒绝未知单位。TTL非法回3s，confidence非法回0并夹[0,1]，target_actor_id映target_id，最终Schema验证。

<a id="fn-perception-frame-to-state"></a>

### `perception_frame_to_state`

源码位置：[integration/canonical_bridge.py 第 121 行](../../../integration/canonical_bridge.py#L121)。类型：`FunctionDef`。

```python
perception_frame_to_state(scene: PerceptionFrame, vehicle: Any, *, captured_at_ns: int, perception_mode: str, registry: InterfaceRegistry | None=None) -> dict[str, Any]
```

从PerceptionFrame构造canonical对象；距离缺失补50m、框中心估横向(0.5-center)*7m、首物体用lead_speed其余补0。保留track_id否则legacy类别索引；risk按碰撞/TTC1.5/2.5s与gap5/10m分类。modality/stale依据模式字符串构造，不是重新验证原始传感帧。

<a id="fn-control-command-to-voice-envelope"></a>

### `control_command_to_voice_envelope`

源码位置：[integration/canonical_bridge.py 第 218 行](../../../integration/canonical_bridge.py#L218)。类型：`FunctionDef`。

```python
control_command_to_voice_envelope(control: Mapping[str, Any], *, source_text: str) -> dict[str, Any]
```

SET_SPEED/SLOW_DOWN需速度，FOLLOW映SLOW_DOWN或KEEP_LANE；STOP/HOLD映STOP。SLOW且QWEN_DECISION_PLAN才允许转弯/变道/PULL_OVER/YIELD，YIELD转SLOW_DOWN且需速度。TTL=max(0.1,(deadline-issued)/1e9)，不能代替上游过期拒绝；不把target_id转成底层执行目标槽位。

## 内部调用与异常路径

- `voice_envelope_to_driving_command` 调用：`InterfaceRegistry`, `bool`, `envelope.get`, `float`, `int`, `intent.endswith`, `isinstance`, `math.isfinite`, `max`, `min`, `parameters.get`, `registry.validate`, `str`, `str(envelope.get('intent', 'UNKNOWN')).upper`, `str(parameters.get('direction', '')).upper`, `str(parameters.get('unit', 'km/h')).lower`, `str(parameters.get('unit', 'km/h')).lower().replace`, `type`, `{'FOLLOW': 'FOLLOW', 'FOLLOW_ROUTE': 'FOLLOW', 'EMERGENCY_STOP': 'EMERGENCY_STOP', 'STOP': 'STOP', 'HOLD': 'STOP', 'SET_SPEED': 'SET_SPEED', 'SLOW_DOWN': 'SLOW_DOWN', 'YIELD': 'YIELD', 'KEEP_LANE': 'KEEP_LANE', 'CHANGE_LANE': 'CHANGE_LANE', 'CHANGE_LANE_LEFT': 'CHANGE_LANE', 'CHANGE_LANE_RIGHT': 'CHANGE_LANE', 'TURN': 'TURN', 'TURN_LEFT': 'TURN', 'TURN_RIGHT': 'TURN', 'PULL_OVER': 'PULL_OVER', 'AVOID_OBSTACLE': 'AVOID_OBSTACLE'}.get`.
- `perception_frame_to_state` 调用：`InterfaceRegistry`, `TypeError`, `_CLASS_MAP.get`, `enumerate`, `float`, `isinstance`, `list`, `objects.append`, `registry.validate`, `str`, `str(item.class_name).lower`, `str(perception_mode).lower`.
- `control_command_to_voice_envelope` 调用：`ValueError`, `behavior.rsplit`, `bool`, `control.get`, `control['target'].get`, `float`, `int`, `max`, `str`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `control_command_to_voice_envelope`，第 231 行：`ValueError(f'{behavior} requires target_speed_mps')`。
- `control_command_to_voice_envelope`，第 239 行：`ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')`。
- `control_command_to_voice_envelope`，第 241 行：`ValueError('YIELD requires target_speed_mps')`。
- `control_command_to_voice_envelope`，第 256 行：`ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')`。
- `control_command_to_voice_envelope`，第 261 行：`ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')`。
- `control_command_to_voice_envelope`，第 266 行：`ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')`。
- `control_command_to_voice_envelope`，第 269 行：`ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')`。
- `perception_frame_to_state`，第 130 行：`TypeError('scene must be PerceptionFrame')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/contracts.py](../../../integration/contracts.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- [integration/second_group_runtime.py](../../../integration/second_group_runtime.py)
- [integration/tests/test_canonical_bridge.py](../../../integration/tests/test_canonical_bridge.py)
- [integration/tests/test_scenario_execution.py](../../../integration/tests/test_scenario_execution.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-canonical-bridge-py"></a>

### `integration/canonical_bridge.py`

来源 SHA256：`f6b5ba676f6297ee0f9928ab5ce5ed180b978bcba04626b8091072c1a83c13e9`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `perception_frame_to_state` / 130 | `not isinstance(scene, PerceptionFrame)` | `raise TypeError('scene must be PerceptionFrame')` |
| `control_command_to_voice_envelope` / 231 | `behavior in {'SET_SPEED', 'SLOW_DOWN'} AND target_speed is None` | `raise ValueError(f'{behavior} requires target_speed_mps')` |
| `control_command_to_voice_envelope` / 239 | `NOT (behavior in {'SET_SPEED', 'SLOW_DOWN'}) AND NOT (behavior == 'FOLLOW') AND behavior == 'YIELD' AND not compiled_maneuver` | `raise ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')` |
| `control_command_to_voice_envelope` / 241 | `NOT (behavior in {'SET_SPEED', 'SLOW_DOWN'}) AND NOT (behavior == 'FOLLOW') AND behavior == 'YIELD' AND target_speed is None` | `raise ValueError('YIELD requires target_speed_mps')` |
| `control_command_to_voice_envelope` / 256 | `NOT (behavior in {'SET_SPEED', 'SLOW_DOWN'}) AND NOT (behavior == 'FOLLOW') AND NOT (behavior == 'YIELD') AND NOT (behavior in {'STOP', 'HOLD'}) AND NOT (behavior == 'EMERGENCY_STOP') AND NOT (behavior == 'KEEP_LANE') AND behavior in {'TURN_LEFT', 'TURN_RIGHT'} AND not compiled_maneuver` | `raise ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')` |
| `control_command_to_voice_envelope` / 261 | `NOT (behavior in {'SET_SPEED', 'SLOW_DOWN'}) AND NOT (behavior == 'FOLLOW') AND NOT (behavior == 'YIELD') AND NOT (behavior in {'STOP', 'HOLD'}) AND NOT (behavior == 'EMERGENCY_STOP') AND NOT (behavior == 'KEEP_LANE') AND NOT (behavior in {'TURN_LEFT', 'TURN_RIGHT'}) AND behavior in {'CHANGE_LANE_LEFT', 'CHANGE_LANE_RIGHT'} AND not compiled_maneuver` | `raise ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')` |
| `control_command_to_voice_envelope` / 266 | `NOT (behavior in {'SET_SPEED', 'SLOW_DOWN'}) AND NOT (behavior == 'FOLLOW') AND NOT (behavior == 'YIELD') AND NOT (behavior in {'STOP', 'HOLD'}) AND NOT (behavior == 'EMERGENCY_STOP') AND NOT (behavior == 'KEEP_LANE') AND NOT (behavior in {'TURN_LEFT', 'TURN_RIGHT'}) AND NOT (behavior in {'CHANGE_LANE_LEFT', 'CHANGE_LANE_RIGHT'}) AND behavior == 'PULL_OVER' AND not compiled_maneuver` | `raise ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')` |
| `control_command_to_voice_envelope` / 269 | `NOT (behavior in {'SET_SPEED', 'SLOW_DOWN'}) AND NOT (behavior == 'FOLLOW') AND NOT (behavior == 'YIELD') AND NOT (behavior in {'STOP', 'HOLD'}) AND NOT (behavior == 'EMERGENCY_STOP') AND NOT (behavior == 'KEEP_LANE') AND NOT (behavior in {'TURN_LEFT', 'TURN_RIGHT'}) AND NOT (behavior in {'CHANGE_LANE_LEFT', 'CHANGE_LANE_RIGHT'}) AND NOT (behavior == 'PULL_OVER')` | `raise ValueError(f'current deterministic runtime cannot execute slow behavior {behavior}')` |

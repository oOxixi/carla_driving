# qwen_command_adapter：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_command_adapter.py](../../../integration/qwen_command_adapter.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Stable adapter from validated Qwen decisions to the A-side command contract.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-build-high-level-command"></a>

### `build_high_level_command`

源码位置：[integration/qwen_command_adapter.py 第 22 行](../../../integration/qwen_command_adapter.py#L22)。类型：`FunctionDef`。

```python
build_high_level_command(decision: Mapping[str, Any], source_text: str, *, command_id: str | None=None, valid_duration_s: float=3.0) -> dict[str, Any]
```

Build the versioned high-level command accepted by the runtime boundary.

<a id="fn-build-command"></a>

### `build_command`

源码位置：[integration/qwen_command_adapter.py 第 74 行](../../../integration/qwen_command_adapter.py#L74)。类型：`FunctionDef`。

```python
build_command(decision: Mapping[str, Any], source_text: str) -> dict[str, Any]
```

Build the frozen A-runtime envelope from a validated Qwen decision.

## 内部调用与异常路径

- `build_high_level_command` 调用：`TypeError`, `ValueError`, `bool`, `decision.get`, `float`, `isinstance`, `math.isfinite`, `max`, `str`, `str(decision.get('action', '')).strip`, `str(decision.get('action', '')).strip().upper`, `target_track_id.strip`, `time.monotonic_ns`, `type`, `uuid.uuid4`.
- `build_command` 调用：`HighLevelCommandAdapter`, `HighLevelCommandAdapter().adapt`, `build_high_level_command`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `build_high_level_command`，第 33 行：`ValueError(f'unsupported Qwen action: {action}')`。
- `build_high_level_command`，第 40 行：`ValueError('valid_duration_s must be finite and positive')`。
- `build_high_level_command`，第 63 行：`TypeError('visual_valid must be bool')`。
- `build_high_level_command`，第 68 行：`TypeError('target_track_id must be a non-empty string')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py)

静态 import 消费者（含测试）：

- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/qwen_async.py](../../../integration/qwen_async.py)
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/tests/test_qwen_boundary.py](../../../integration/tests/test_qwen_boundary.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)
- [tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-command-adapter-py"></a>

### `integration/qwen_command_adapter.py`

来源 SHA256：`8001c8042be543dfae846b60ece228aafbd8fdb32d78ef626decb6cbfcd64284`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `build_high_level_command` / 33 | `action not in SUPPORTED_INTENTS` | `raise ValueError(f'unsupported Qwen action: {action}')` |
| `build_high_level_command` / 40 | `type(valid_duration_s) not in (int, float) or isinstance(valid_duration_s, bool) or (not math.isfinite(float(valid_duration_s))) or (valid_duration_s <= 0.0)` | `raise ValueError('valid_duration_s must be finite and positive')` |
| `build_high_level_command` / 63 | `'visual_valid' in decision AND type(visual_valid) is not bool` | `raise TypeError('visual_valid must be bool')` |
| `build_high_level_command` / 68 | `'target_track_id' in decision AND type(target_track_id) is not str or not target_track_id.strip()` | `raise TypeError('target_track_id must be a non-empty string')` |

## 实际转换边界（逐实现复核）

`build_high_level_command(decision, source_text, command_id=None, valid_duration_s=3.0)` 只接受 START/STOP/SLOW_DOWN/SET_SPEED/EMERGENCY_STOP，不是 canonical FOLLOW/多步计划转换器。action 去空白转大写；TTL须有限正秒数，未给ID生成 `qwen_` 加8位UUID，timestamp_ns使用本机单调时钟。confidence默认0并转float、requires_confirmation默认False并转bool；此函数假定输入已经过边界校验，不能替代 validate_qwen_response。

SET_SPEED/SLOW_DOWN 的非空 target_speed_mps 转float并下限截0，不在这里限制最大速度。可选 visual_valid 必须是bool，target_track_id必须非空字符串并strip；其他行为不复制速度。reason_zh默认空、decision_source默认UNKNOWN。`build_command` 再交给 HighLevelCommandAdapter 转冻结车辆envelope；异常继续向上传播，不增加重试或后台执行。

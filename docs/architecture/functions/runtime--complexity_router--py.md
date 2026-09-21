# complexity_router：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[runtime/complexity_router.py](../../../runtime/complexity_router.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Deterministic, explainable constraints for Qwen-routed driving commands.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ComplexityFeatures.atomic_action_count: int`；默认：`未在声明处设置`。
- `ComplexityFeatures.has_sequence: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.has_condition: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.has_visual_reference: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.has_route_reference: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.target_candidate_count: int`；默认：`未在声明处设置`。
- `ComplexityFeatures.target_is_unique: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.has_scene_conflict: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.has_modality_disagreement: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.requires_maneuver: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.parameters_complete: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.command_confidence: float`；默认：`未在声明处设置`。
- `ComplexityFeatures.perception_fresh: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.requires_replan: bool`；默认：`未在声明处设置`。
- `ComplexityFeatures.reason_codes: tuple[str, ...]`；默认：`未在声明处设置`。
- `QwenRoutingDecision.disposition: str`；默认：`未在声明处设置`。
- `QwenRoutingDecision.score: int`；默认：`未在声明处设置`。
- `QwenRoutingDecision.reasons: tuple[str, ...]`；默认：`未在声明处设置`。
- `QwenRoutingDecision.features: ComplexityFeatures`；默认：`未在声明处设置`。
- `QwenRoutingDecision.safe_wait_behavior: str`；默认：`未在声明处设置`。
- `QwenRoutingDecision.expected_qwen_calls: int`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-complexityfeatures"></a>

### `ComplexityFeatures`

源码位置：[runtime/complexity_router.py 第 76 行](../../../runtime/complexity_router.py#L76)。类型：`ClassDef`。

路由特征快照：动作数、时序/条件/视觉/路线引用、候选数与唯一性、场景/模态冲突、maneuver、参数完整性、置信度、新鲜度与 replan。基于规则与输入元数据，不是另一个学习模型的分类结果。

<a id="fn-complexityfeatures-to-dict"></a>

### `ComplexityFeatures.to_dict`

源码位置：[runtime/complexity_router.py 第 93 行](../../../runtime/complexity_router.py#L93)。类型：`FunctionDef`。

```python
ComplexityFeatures.to_dict(self) -> dict[str, Any]
```

导出 dataclass 字段字典，reason_codes 转列表供 JSON 日志；不重算特征或检查输入场景。

<a id="fn-qwenroutingdecision"></a>

### `QwenRoutingDecision`

源码位置：[runtime/complexity_router.py 第 100 行](../../../runtime/complexity_router.py#L100)。类型：`ClassDef`。

包含 disposition、score、reasons、features、safe_wait_behavior、expected_qwen_calls；两种合法路由都预期调用 Qwen 一次，safe_wait_behavior 是建议，实际 bridge 等待控制另行生成。

<a id="fn-complexityrouter"></a>

### `ComplexityRouter`

源码位置：[runtime/complexity_router.py 第 109 行](../../../runtime/complexity_router.py#L109)。类型：`ClassDef`。

Apply safety gates, hard routing triggers, then an explainable score.

<a id="fn-complexityrouter---init--"></a>

### `ComplexityRouter.__init__`

源码位置：[runtime/complexity_router.py 第 112 行](../../../runtime/complexity_router.py#L112)。类型：`FunctionDef`。

```python
ComplexityRouter.__init__(self, *, minimum_confidence: float=0.8, qwen_score: int=3) -> None
```

minimum_confidence 默认0.80并要求[0,1]，qwen_score 默认3且须正整数；保存规则阈值，不创建模型或线程。

<a id="fn-complexityrouter-decide"></a>

### `ComplexityRouter.decide`

源码位置：[runtime/complexity_router.py 第 120 行](../../../runtime/complexity_router.py#L120)。类型：`FunctionDef`。

```python
ComplexityRouter.decide(self, command: Mapping[str, Any], perception: Mapping[str, Any], runtime_state: Mapping[str, Any] | None=None) -> QwenRoutingDecision
```

从命令文字、canonical 参数、感知与 runtime_state 提取特征。优先级为急停/STOP→QWEN_PLAN（score=-5），感知过期/违法/严重歧义/不唯一视觉目标→CONFIRM_SAFE，明确原子命令→QWEN_PLAN（-4），复杂条件或score>=阈值→QWEN_PLAN，否则CONFIRM_SAFE。两条路由都送模型；多动作+3、时序或条件+3、视觉或多候选+3、maneuver+2、场景或模态冲突+2、replan+2、参数不完整+1。

<a id="fn-complexityrouter--decision"></a>

### `ComplexityRouter._decision`

源码位置：[runtime/complexity_router.py 第 288 行](../../../runtime/complexity_router.py#L288)。类型：`FunctionDef`。

```python
ComplexityRouter._decision(disposition: str, score: int, reasons: tuple[str, ...], actions: set[str], has_sequence: bool, has_condition: bool, has_visual: bool, has_route: bool, candidate_count: int, target_unique: bool, scene_conflict: bool, modality_disagreement: bool, requires_maneuver: bool, parameters_complete: bool, confidence: float, perception_fresh: bool, requires_replan: bool, safe_wait: str) -> QwenRoutingDecision
```

对原因码按首次出现顺序去重，构造特征及结果；expected_qwen_calls 固定1，包括 CONFIRM_SAFE。不会在此函数下发 safe_wait_behavior 给车辆。

<a id="fn--normalized-text"></a>

### `_normalized_text`

源码位置：[runtime/complexity_router.py 第 338 行](../../../runtime/complexity_router.py#L338)。类型：`FunctionDef`。

```python
_normalized_text(text: str) -> str
```

转小写并删除空白/标点，供中英文规则匹配；不进行 ASR纠错、分词或外部 NLU 调用。

<a id="fn--confidence"></a>

### `_confidence`

源码位置：[runtime/complexity_router.py 第 342 行](../../../runtime/complexity_router.py#L342)。类型：`FunctionDef`。

```python
_confidence(value: Any) -> float
```

非数值输入按0，数值 clamp 到[0,1]；是宽容特征提取，不能代替上游 Schema 和严格有限数检查。

<a id="fn--nested"></a>

### `_nested`

源码位置：[runtime/complexity_router.py 第 348 行](../../../runtime/complexity_router.py#L348)。类型：`FunctionDef`。

```python
_nested(payload: Mapping[str, Any], outer: str, inner: str, *, default: Any) -> Any
```

取嵌套 mapping；缺失或值不是 Mapping 时返回空映射，方便规则降级，不抛缺键异常。

<a id="fn--actions"></a>

### `_actions`

源码位置：[runtime/complexity_router.py 第 353 行](../../../runtime/complexity_router.py#L353)。类型：`FunctionDef`。

```python
_actions(text: str, intent: str) -> set[str]
```

用规范化文本规则和 intent 收集动作集合；SLOW_DOWN 命中时去掉速度设置匹配，避免同一句减速重复计数。不是顺序动作解析器，顺序/条件用独立特征记录。

<a id="fn--parameters-complete"></a>

### `_parameters_complete`

源码位置：[runtime/complexity_router.py 第 384 行](../../../runtime/complexity_router.py#L384)。类型：`FunctionDef`。

```python
_parameters_complete(command: Mapping[str, Any]) -> bool
```

SET_SPEED 检查速度键是否存在；转弯/变道核对方向；FOLLOW 显式目标或其他可接受描述按规则处理；未知意图不完整。键存在不等于数值有效，最终契约校验仍由 Schema/Validator 负责。

<a id="fn--target-candidates"></a>

### `_target_candidates`

源码位置：[runtime/complexity_router.py 第 397 行](../../../runtime/complexity_router.py#L397)。类型：`FunctionDef`。

```python
_target_candidates(command: Mapping[str, Any], perception: Mapping[str, Any], runtime: Mapping[str, Any], text: str, has_visual: bool) -> tuple[int, bool]
```

优先 runtime_state、再 perception 的合法显式候选数/唯一性；否则按 target ID、视觉类别与前左/前右等空间规则计数。它返回候选数量和唯一性，不产生 actor↔track alias 或最终目标 ID。

<a id="fn--scene-conflict"></a>

### `_scene_conflict`

源码位置：[runtime/complexity_router.py 第 448 行](../../../runtime/complexity_router.py#L448)。类型：`FunctionDef`。

```python
_scene_conflict(command: Mapping[str, Any], perception: Mapping[str, Any], runtime: Mapping[str, Any], text: str, illegal: bool) -> bool
```

根据违法标记、runtime 冲突或红/黄灯下的前进语义判断冲突；纯规则布尔值，不执行几何碰撞预测。

<a id="fn--safe-wait-behavior"></a>

### `_safe_wait_behavior`

源码位置：[runtime/complexity_router.py 第 466 行](../../../runtime/complexity_router.py#L466)。类型：`FunctionDef`。

```python
_safe_wait_behavior(perception: Mapping[str, Any], runtime: Mapping[str, Any]) -> str
```

急停推荐 EMERGENCY_STOP；stale/不同步/HIGH或UNKNOWN风险推荐STOP；CAUTION或冲突推荐SLOW_DOWN；其余KEEP_LANE_LIMITED。CanonicalRuntimeBridge 实际等待阶段仍使用独立 STOP/EMERGENCY_STOP envelope，不应把这里的建议当作已执行行为。

## 内部调用与异常路径

- `_normalized_text` 调用：`re.sub`, `re.sub('[，。！？、,.!?\\s]+', '', text.strip()).lower`, `text.strip`.
- `_confidence` 调用：`float`, `isinstance`, `max`, `min`, `type`.
- `_nested` 调用：`isinstance`, `payload.get`, `value.get`.
- `_actions` 调用：`found.add`, `found.discard`, `pattern.search`, `{'CHANGE_LANE_LEFT', 'CHANGE_LANE_RIGHT'}.intersection`, `{'START': 'START', 'STOP': 'STOP', 'EMERGENCY_STOP': 'STOP', 'SET_SPEED': 'SET_SPEED', 'SLOW_DOWN': 'SLOW_DOWN', 'KEEP_LANE': 'KEEP_LANE', 'FOLLOW': 'FOLLOW', 'YIELD': 'YIELD', 'PULL_OVER': 'PULL_OVER', 'AVOID_OBSTACLE': 'AVOID_OBSTACLE'}.get`, `{'TURN_LEFT', 'TURN_RIGHT'}.intersection`.
- `_parameters_complete` 调用：`bool`, `command.get`, `isinstance`, `parameters.get`, `str`, `str(command.get('intent', 'UNKNOWN')).upper`, `str(parameters.get('direction', '')).upper`, `str(parameters['target_id']).strip`.
- `_target_candidates` 调用：`any`, `bool`, `candidates.append`, `command.get`, `float`, `isinstance`, `item.get`, `len`, `parameters.get`, `perception.get`, `runtime.get`, `str`, `str(item.get('class', 'unknown')).lower`, `sum`, `text.lower`, `type`.
- `_scene_conflict` 调用：`any`, `bool`, `perception.get`, `re.search`, `runtime.get`, `str`, `str(perception.get('traffic_light', 'UNKNOWN')).upper`, `text.lower`.
- `_safe_wait_behavior` 调用：`_nested`, `bool`, `perception.get`, `runtime.get`, `str`, `str(perception.get('risk_level', 'UNKNOWN')).upper`.
- `to_dict` 调用：`asdict`, `list`.
- `__init__` 调用：`ValueError`, `float`, `type`.
- `decide` 调用：`TypeError`, `_CONDITION_RE.search`, `_ILLEGAL_RE.search`, `_ROUTE_RE.search`, `_SEQUENCE_RE.search`, `_SEVERE_AMBIGUITY_RE.fullmatch`, `_VISUAL_RE.search`, `_actions`, `_confidence`, `_nested`, `_normalized_text`, `_parameters_complete`, `_safe_wait_behavior`, `_scene_conflict`, `_target_candidates`, `any`, `bool`, `command.get`, `isinstance`, `len`, `perception.get`, `reasons.append`, `reasons.extend`, `runtime.get`, `self._decision`, `str`, `str(command.get('intent', 'UNKNOWN')).upper`, `str(command.get('source_text', '')).strip`, `str(perception.get('risk_level', 'UNKNOWN')).upper`, `str(runtime.get('replan_reason', '')).strip`, `str(runtime.get('replan_reason', '')).strip().upper`, `tuple`.
- `_decision` 调用：`ComplexityFeatures`, `QwenRoutingDecision`, `dict.fromkeys`, `len`, `tuple`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 114 行：`ValueError('minimum_confidence must be in [0, 1]')`。
- `__init__`，第 116 行：`ValueError('qwen_score must be a positive integer')`。
- `decide`，第 127 行：`TypeError('command and perception must be mappings')`。
- `decide`，第 130 行：`TypeError('runtime_state must be a mapping or None')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/qwen_plan_adapter.py](../../../integration/qwen_plan_adapter.py)
- [integration/tests/test_qwen_plan_boundary.py](../../../integration/tests/test_qwen_plan_boundary.py)
- [runtime/__init__.py](../../../runtime/__init__.py)
- [runtime/orchestrator.py](../../../runtime/orchestrator.py)
- [runtime/tests/test_complexity_router.py](../../../runtime/tests/test_complexity_router.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-runtime-complexity-router-py"></a>

### `runtime/complexity_router.py`

来源 SHA256：`d1785c61f636ebba3fa8b848c67502fd630c352a6ed4feb664546d76d5408a1c`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ComplexityFeatures.atomic_action_count` | `int` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.has_sequence` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.has_condition` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.has_visual_reference` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.has_route_reference` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.target_candidate_count` | `int` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.target_is_unique` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.has_scene_conflict` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.has_modality_disagreement` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.requires_maneuver` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.parameters_complete` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.command_confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.perception_fresh` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.requires_replan` | `bool` | `无声明默认；构造/赋值方提供` |
| `ComplexityFeatures.reason_codes` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `QwenRoutingDecision.disposition` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenRoutingDecision.score` | `int` | `无声明默认；构造/赋值方提供` |
| `QwenRoutingDecision.reasons` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `QwenRoutingDecision.features` | `ComplexityFeatures` | `无声明默认；构造/赋值方提供` |
| `QwenRoutingDecision.safe_wait_behavior` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenRoutingDecision.expected_qwen_calls` | `int` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `ComplexityRouter.__init__` / 114 | `not 0.0 <= float(minimum_confidence) <= 1.0` | `raise ValueError('minimum_confidence must be in [0, 1]')` |
| `ComplexityRouter.__init__` / 116 | `type(qwen_score) is not int or qwen_score < 1` | `raise ValueError('qwen_score must be a positive integer')` |
| `ComplexityRouter.decide` / 127 | `not isinstance(command, Mapping) or not isinstance(perception, Mapping)` | `raise TypeError('command and perception must be mappings')` |
| `ComplexityRouter.decide` / 130 | `not isinstance(runtime, Mapping)` | `raise TypeError('runtime_state must be a mapping or None')` |

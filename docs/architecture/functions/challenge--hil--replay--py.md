# replay：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/replay.py](../../../challenge/hil/replay.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Replay of frozen B1 request sets through the planner under test.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ReplayCase.case_id: str`；默认：`未在声明处设置`。
- `ReplayCase.sample_id: str`；默认：`未在声明处设置`。
- `ReplayCase.scenario_id: str`；默认：`未在声明处设置`。
- `ReplayCase.request: dict[str, Any]`；默认：`未在声明处设置`。
- `ReplayCase.teacher_plan: dict[str, Any] | None`；默认：`未在声明处设置`。
- `ReplayCase.rgb_path: str | None`；默认：`未在声明处设置`。
- `ReplayCase.rgb_sha256: str | None`；默认：`未在声明处设置`。
- `ReplayCase.rgb_resolved: bool`；默认：`未在声明处设置`。
- `ReplayCase.rgb_source: str`；默认：`未在声明处设置`。
- `ReplayCase.source_file: str`；默认：`未在声明处设置`。
- `ReplayResult.rows: list[dict[str, Any]]`；默认：`field(default_factory=list)`。
- `ReplayResult.traces: list[StageTrace]`；默认：`field(default_factory=list)`。
- `ReplayResult.plans: list[dict[str, Any]]`；默认：`field(default_factory=list)`。
- `ReplayResult.summary: dict[str, Any]`；默认：`field(default_factory=dict)`。

## 功能入口：输入、输出与实现说明

### `ReplayCase`

源码位置：[challenge/hil/replay.py 第 42 行](../../../challenge/hil/replay.py#L42)。类型：`ClassDef`。

`ReplayCase` HIL协议类，封装runtime、能力、身份、trace、回放、轮次或采样状态；默认字段不是实测结果，必须随证据序列化。

### `ReplayResult`

源码位置：[challenge/hil/replay.py 第 56 行](../../../challenge/hil/replay.py#L56)。类型：`ClassDef`。

`ReplayResult` HIL协议类，封装runtime、能力、身份、trace、回放、轮次或采样状态；默认字段不是实测结果，必须随证据序列化。

### `_rgb_index`

源码位置：[challenge/hil/replay.py 第 63 行](../../../challenge/hil/replay.py#L63)。类型：`FunctionDef`。

```python
_rgb_index(delivery_root: Path | None) -> dict[str, dict[str, Any]]
```

`_rgb_index` 读取冻结输入、配置、图像或provenance；路径解析必须保持发布边界，缺失资源不能静默当作成功样本。

### `_resolve_rgb`

源码位置：[challenge/hil/replay.py 第 92 行](../../../challenge/hil/replay.py#L92)。类型：`FunctionDef`。

```python
_resolve_rgb(request: Mapping[str, Any], *, sample_id: str, manifest_entry: Mapping[str, Any] | None, delivery_root: Path | None, repo_root: Path | None) -> tuple[str | None, str | None, bool, str]
```

Return (path, sha256, resolved, source).

### `load_replay_cases`

源码位置：[challenge/hil/replay.py 第 128 行](../../../challenge/hil/replay.py#L128)。类型：`FunctionDef`。

```python
load_replay_cases(*, delivery_root: str | Path | None, requests_path: str | Path | None=None, repo_root: str | Path | None=None, limit: int | None=None) -> tuple[list[ReplayCase], dict[str, Any]]
```

`load_replay_cases` 读取冻结输入、配置、图像或provenance；路径解析必须保持发布边界，缺失资源不能静默当作成功样本。

### `_behaviors`

源码位置：[challenge/hil/replay.py 第 200 行](../../../challenge/hil/replay.py#L200)。类型：`FunctionDef`。

```python
_behaviors(plan: Mapping[str, Any] | None) -> list[str]
```

`_behaviors` 更新trace/collector状态或派生运行辅助值；阶段顺序、重复mark、能力声明和错误传播受源码条件约束，不能仅凭名称推断。

### `_targets`

源码位置：[challenge/hil/replay.py 第 213 行](../../../challenge/hil/replay.py#L213)。类型：`FunctionDef`。

```python
_targets(plan: Mapping[str, Any] | None) -> list[str]
```

`_targets` 更新trace/collector状态或派生运行辅助值；阶段顺序、重复mark、能力声明和错误传播受源码条件约束，不能仅凭名称推断。

### `_match_ratio`

源码位置：[challenge/hil/replay.py 第 231 行](../../../challenge/hil/replay.py#L231)。类型：`FunctionDef`。

```python
_match_ratio(left: Sequence[str], right: Sequence[str]) -> float
```

`_match_ratio` 更新trace/collector状态或派生运行辅助值；阶段顺序、重复mark、能力声明和错误传播受源码条件约束，不能仅凭名称推断。

### `structural_checks`

源码位置：[challenge/hil/replay.py 第 241 行](../../../challenge/hil/replay.py#L241)。类型：`FunctionDef`。

```python
structural_checks(request: Mapping[str, Any], plan: Mapping[str, Any] | None) -> tuple[str, ...]
```

`structural_checks` 检查runtime合同、artifact、输出一致性、结构或身份完整性；结果只覆盖声明能力，model-only与full-chain、宿主与板端证据不得混写。

### `run_replay`

源码位置：[challenge/hil/replay.py 第 278 行](../../../challenge/hil/replay.py#L278)。类型：`FunctionDef`。

```python
run_replay(runtime: PlannerRuntime, cases: Iterable[ReplayCase], *, run_id: str, round_index: int, phase: str='measured') -> ReplayResult
```

`run_replay` 执行轮次、回放、长稳、子命令、benchmark或后台采样；warmup与measured分离，错误/超时/缺stage必须作为结果记录而非零时延。

### `failure_row_detail`

源码位置：[challenge/hil/replay.py 第 368 行](../../../challenge/hil/replay.py#L368)。类型：`FunctionDef`。

```python
failure_row_detail(trace: StageTrace) -> dict[str, Any]
```

`failure_row_detail` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

## 内部调用与异常路径

- `_rgb_index` 调用：`entry.get`, `isinstance`, `path.is_file`, `payload.get`, `payload.items`, `read_json`, `release_path.is_file`, `str`, `value.get`.
- `_resolve_rgb` 调用：`(root / packaged).resolve`, `(root / reference).resolve`, `actual.lower`, `candidate.is_file`, `digest.lower`, `isinstance`, `manifest_entry.get`, `reference.strip`, `request.get`, `sha256_file`, `str`.
- `load_replay_cases` 调用：`FileNotFoundError`, `Path`, `Path(delivery_root).resolve`, `Path(repo_root).resolve`, `Path(requests_path).resolve`, `ReplayCase`, `ValueError`, `_resolve_rgb`, `_rgb_index`, `bool`, `candidate.is_file`, `cases.append`, `copy.deepcopy`, `dict`, `enumerate`, `isinstance`, `len`, `list`, `manifest.get`, `metadata.get`, `read_jsonl`, `record.get`, `str`.
- `_behaviors` 调用：`isinstance`, `plan.get`, `step.get`, `str`, `values.append`.
- `_targets` 调用：`isinstance`, `plan.get`, `step.get`, `str`, `target.get`, `values.append`.
- `_match_ratio` 调用：`len`, `max`, `min`, `range`, `sum`.
- `structural_checks` 调用：`'|'.join`, `_behaviors`, `bool`, `enumerate`, `failures.append`, `isinstance`, `len`, `plan.get`, `request.get`, `request.get('constraints', {}).get`, `tuple`.
- `run_replay` 调用：`'|'.join`, `ReplayResult`, `_behaviors`, `_match_ratio`, `_targets`, `case.request.get`, `identity.get`, `len`, `list`, `plans.append`, `rows.append`, `runtime.identity.to_dict`, `runtime.infer`, `structural_checks`, `traces.append`.
- `failure_row_detail` 调用：`list`, `trace.durations_ms`, `trace.durations_ms().get`, `trace.missing_stages`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `load_replay_cases`，第 140 行：`ValueError('either requests_path or delivery_root is required')`。
- `load_replay_cases`，第 147 行：`FileNotFoundError(f'no request JSONL found under {delivery}; tried {REQUEST_SOURCE_PREFERENCE}')`。
- `load_replay_cases`，第 157 行：`ValueError(f'{source}: record {index} has no model_request object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/identity.py](../../../challenge/hil/identity.py)
- [challenge/hil/run_io.py](../../../challenge/hil/run_io.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)
- [challenge/hil/stages.py](../../../challenge/hil/stages.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/contract.py](../../../challenge/hil/contract.py)
- [challenge/hil/failure_cases.py](../../../challenge/hil/failure_cases.py)
- [challenge/hil/freeze.py](../../../challenge/hil/freeze.py)
- [challenge/hil/rounds.py](../../../challenge/hil/rounds.py)
- [challenge/hil/stability.py](../../../challenge/hil/stability.py)
- [challenge/hil/tests/test_freeze_stability_handoff.py](../../../challenge/hil/tests/test_freeze_stability_handoff.py)
- [challenge/hil/tests/test_replay_and_failures.py](../../../challenge/hil/tests/test_replay_and_failures.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/replay.py`

来源 SHA256：`f6858214f9622804160d89038b71cebee5a8c4f62e94bd217d67dfcbb1c482be`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ReplayCase.case_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.sample_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.scenario_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.request` | `dict[str, Any]` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.teacher_plan` | `dict[str, Any] &#124; None` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.rgb_path` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.rgb_sha256` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.rgb_resolved` | `bool` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.rgb_source` | `str` | `无声明默认；构造/赋值方提供` |
| `ReplayCase.source_file` | `str` | `无声明默认；构造/赋值方提供` |
| `ReplayResult.rows` | `list[dict[str, Any]]` | `field(default_factory=list)` |
| `ReplayResult.traces` | `list[StageTrace]` | `field(default_factory=list)` |
| `ReplayResult.plans` | `list[dict[str, Any]]` | `field(default_factory=list)` |
| `ReplayResult.summary` | `dict[str, Any]` | `field(default_factory=dict)` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `load_replay_cases` / 140 | `source is None AND delivery is None` | `raise ValueError('either requests_path or delivery_root is required')` |
| `load_replay_cases` / 147 | `source is None AND source is None` | `raise FileNotFoundError(f'no request JSONL found under {delivery}; tried {REQUEST_SOURCE_PREFERENCE}')` |
| `load_replay_cases` / 157 | `not isinstance(request, Mapping)` | `raise ValueError(f'{source}: record {index} has no model_request object')` |

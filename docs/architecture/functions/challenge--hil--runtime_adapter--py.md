# runtime_adapter：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Adapters for the three measurement chains.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RuntimeCapabilities.full_chain: bool`；默认：`未在声明处设置`。
- `RuntimeCapabilities.model_only: bool`；默认：`未在声明处设置`。
- `RuntimeCapabilities.plan_validator: bool`；默认：`未在声明处设置`。
- `RuntimeCapabilities.stage_source: str`；默认：`未在声明处设置`。
- `RuntimeCapabilities.notes: tuple[str, ...]`；默认：`()`。
- `PlannerRuntime.name: str`；默认：`未在声明处设置`。
- `PlannerRuntime.identity: CandidateIdentity`；默认：`未在声明处设置`。
- `PlannerRuntime.capabilities: RuntimeCapabilities`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `AdapterError`

源码位置：[challenge/hil/runtime_adapter.py 第 34 行](../../../challenge/hil/runtime_adapter.py#L34)。类型：`ClassDef`。

The adapter could not be constructed or driven.

### `RuntimeCapabilities`

源码位置：[challenge/hil/runtime_adapter.py 第 39 行](../../../challenge/hil/runtime_adapter.py#L39)。类型：`ClassDef`。

`RuntimeCapabilities` HIL协议类，封装runtime、能力、身份、trace、回放、轮次或采样状态；默认字段不是实测结果，必须随证据序列化。

### `RuntimeCapabilities.to_dict`

源码位置：[challenge/hil/runtime_adapter.py 第 46 行](../../../challenge/hil/runtime_adapter.py#L46)。类型：`FunctionDef`。

```python
RuntimeCapabilities.to_dict(self) -> dict[str, Any]
```

`to_dict` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

### `PlannerRuntime`

源码位置：[challenge/hil/runtime_adapter.py 第 56 行](../../../challenge/hil/runtime_adapter.py#L56)。类型：`ClassDef`。

`PlannerRuntime` HIL协议类，封装runtime、能力、身份、trace、回放、轮次或采样状态；默认字段不是实测结果，必须随证据序列化。

### `PlannerRuntime.infer`

源码位置：[challenge/hil/runtime_adapter.py 第 61 行](../../../challenge/hil/runtime_adapter.py#L61)。类型：`FunctionDef`。

```python
PlannerRuntime.infer(self, request: Mapping[str, Any], *, case_id: str, round_index: int, phase: str='measured') -> tuple[Mapping[str, Any] | None, StageTrace]
```

`infer` 执行一次被测推理、输出抓取或外部探针读取；返回计划、Head或遥测必须与对应capability、stage_source和clock_domain一起解释。

### `PlannerRuntime.close`

源码位置：[challenge/hil/runtime_adapter.py 第 71 行](../../../challenge/hil/runtime_adapter.py#L71)。类型：`FunctionDef`。

```python
PlannerRuntime.close(self) -> None
```

`close` 释放runtime、会话、线程或子进程资源；应在异常路径也调用，关闭成功不补齐此前缺失的trace或证据。

### `_RepoModules`

源码位置：[challenge/hil/runtime_adapter.py 第 75 行](../../../challenge/hil/runtime_adapter.py#L75)。类型：`ClassDef`。

Lazy import of the challenge-side modules under test.

### `_RepoModules.__init__`

源码位置：[challenge/hil/runtime_adapter.py 第 78 行](../../../challenge/hil/runtime_adapter.py#L78)。类型：`FunctionDef`。

```python
_RepoModules.__init__(self, repo_root: str | Path) -> None
```

`__init__` 固化runtime、trace、身份、采样器或结果容器的依赖和初始状态，并执行源码中的参数约束；运行证据还需完整identity与时钟域。

### `_RepoModules.get`

源码位置：[challenge/hil/runtime_adapter.py 第 86 行](../../../challenge/hil/runtime_adapter.py#L86)。类型：`FunctionDef`。

```python
_RepoModules.get(self, dotted: str) -> Any
```

`get` 更新trace/collector状态或派生运行辅助值；阶段顺序、重复mark、能力声明和错误传播受源码条件约束，不能仅凭名称推断。

### `_RepoModules.has`

源码位置：[challenge/hil/runtime_adapter.py 第 101 行](../../../challenge/hil/runtime_adapter.py#L101)。类型：`FunctionDef`。

```python
_RepoModules.has(self, dotted: str) -> bool
```

`has` 更新trace/collector状态或派生运行辅助值；阶段顺序、重复mark、能力声明和错误传播受源码条件约束，不能仅凭名称推断。

### `state_dict_fingerprint`

源码位置：[challenge/hil/runtime_adapter.py 第 109 行](../../../challenge/hil/runtime_adapter.py#L109)。类型：`FunctionDef`。

```python
state_dict_fingerprint(model: Any) -> str
```

Deterministic SHA256 over a model's parameters.

The in-process chain has no weight file on disk, so without this the run's
identity would be ``UNRESOLVED`` and the evidence could not say *which*
weights produced the numbers.  Hashing the tensors gives the torch path an
artifact identity that is reproducible (same seed, same weights, same hash).

### `InProcessStudentRuntime`

源码位置：[challenge/hil/runtime_adapter.py 第 128 行](../../../challenge/hil/runtime_adapter.py#L128)。类型：`ClassDef`。

Full-chain measurement reusing A1/A3 objects with B3 timestamps.

### `InProcessStudentRuntime.__init__`

源码位置：[challenge/hil/runtime_adapter.py 第 133 行](../../../challenge/hil/runtime_adapter.py#L133)。类型：`FunctionDef`。

```python
InProcessStudentRuntime.__init__(self, repo_root: str | Path, *, weights: str | Path | None=None, weights_manifest: str | Path | None=None, dataset_version: str=UNRESOLVED, seed: int | None=20260911) -> None
```

`__init__` 固化runtime、trace、身份、采样器或结果容器的依赖和初始状态，并执行源码中的参数约束；运行证据还需完整identity与时钟域。

### `InProcessStudentRuntime.infer`

源码位置：[challenge/hil/runtime_adapter.py 第 219 行](../../../challenge/hil/runtime_adapter.py#L219)。类型：`FunctionDef`。

```python
InProcessStudentRuntime.infer(self, request: Mapping[str, Any], *, case_id: str, round_index: int, phase: str='measured') -> tuple[Mapping[str, Any] | None, StageTrace]
```

`infer` 执行一次被测推理、输出抓取或外部探针读取；返回计划、Head或遥测必须与对应capability、stage_source和clock_domain一起解释。

### `InProcessStudentRuntime.verify_consistency`

源码位置：[challenge/hil/runtime_adapter.py 第 284 行](../../../challenge/hil/runtime_adapter.py#L284)。类型：`FunctionDef`。

```python
InProcessStudentRuntime.verify_consistency(self, request: Mapping[str, Any]) -> dict[str, Any]
```

Prove the instrumented path equals ``StudentBackend.infer`` output.

### `InProcessStudentRuntime.close`

源码位置：[challenge/hil/runtime_adapter.py 第 330 行](../../../challenge/hil/runtime_adapter.py#L330)。类型：`FunctionDef`。

```python
InProcessStudentRuntime.close(self) -> None
```

`close` 释放runtime、会话、线程或子进程资源；应在异常路径也调用，关闭成功不补齐此前缺失的trace或证据。

### `OnnxModelRuntime`

源码位置：[challenge/hil/runtime_adapter.py 第 334 行](../../../challenge/hil/runtime_adapter.py#L334)。类型：`ClassDef`。

Model-only chain: the X86 stand-in for `hrt_model_exec perf`.

### `OnnxModelRuntime.__init__`

源码位置：[challenge/hil/runtime_adapter.py 第 339 行](../../../challenge/hil/runtime_adapter.py#L339)。类型：`FunctionDef`。

```python
OnnxModelRuntime.__init__(self, repo_root: str | Path, onnx_path: str | Path) -> None
```

`__init__` 固化runtime、trace、身份、采样器或结果容器的依赖和初始状态，并执行源码中的参数约束；运行证据还需完整identity与时钟域。

### `OnnxModelRuntime.infer`

源码位置：[challenge/hil/runtime_adapter.py 第 387 行](../../../challenge/hil/runtime_adapter.py#L387)。类型：`FunctionDef`。

```python
OnnxModelRuntime.infer(self, request: Mapping[str, Any], *, case_id: str, round_index: int, phase: str='measured') -> tuple[Mapping[str, Any] | None, StageTrace]
```

`infer` 执行一次被测推理、输出抓取或外部探针读取；返回计划、Head或遥测必须与对应capability、stage_source和clock_domain一起解释。

### `OnnxModelRuntime.bench_model_only`

源码位置：[challenge/hil/runtime_adapter.py 第 446 行](../../../challenge/hil/runtime_adapter.py#L446)。类型：`FunctionDef`。

```python
OnnxModelRuntime.bench_model_only(self, request: Mapping[str, Any], *, iterations: int=10, warmup: int=5, case_id: str='') -> list[StageTrace]
```

Pure forward-pass timing, matching the `perf` tool convention.

### `OnnxModelRuntime.close`

源码位置：[challenge/hil/runtime_adapter.py 第 478 行](../../../challenge/hil/runtime_adapter.py#L478)。类型：`FunctionDef`。

```python
OnnxModelRuntime.close(self) -> None
```

`close` 释放runtime、会话、线程或子进程资源；应在异常路径也调用，关闭成功不补齐此前缺失的trace或证据。

### `BoardCliRuntime`

源码位置：[challenge/hil/runtime_adapter.py 第 482 行](../../../challenge/hil/runtime_adapter.py#L482)。类型：`ClassDef`。

Drive A4's board runtime as a subprocess.

Contract: the runtime reads one ``ModelRequest`` JSON object on stdin and
writes one plan JSON object on stdout.  If the runtime also emits
``{"trace": {"<stage>": <monotonic_ns>}}`` the harness uses those marks;
otherwise the chain is reported as ``NOT_INSTRUMENTED`` and only the
host-measured envelope is available.

### `BoardCliRuntime.__init__`

源码位置：[challenge/hil/runtime_adapter.py 第 494 行](../../../challenge/hil/runtime_adapter.py#L494)。类型：`FunctionDef`。

```python
BoardCliRuntime.__init__(self, command: str | Sequence[str], *, artifact: str | Path | None=None, model_id: str=UNRESOLVED, config_id: str=UNRESOLVED, dataset_version: str=UNRESOLVED, timeout_s: float=30.0) -> None
```

`__init__` 固化runtime、trace、身份、采样器或结果容器的依赖和初始状态，并执行源码中的参数约束；运行证据还需完整identity与时钟域。

### `BoardCliRuntime.infer`

源码位置：[challenge/hil/runtime_adapter.py 第 531 行](../../../challenge/hil/runtime_adapter.py#L531)。类型：`FunctionDef`。

```python
BoardCliRuntime.infer(self, request: Mapping[str, Any], *, case_id: str, round_index: int, phase: str='measured') -> tuple[Mapping[str, Any] | None, StageTrace]
```

`infer` 执行一次被测推理、输出抓取或外部探针读取；返回计划、Head或遥测必须与对应capability、stage_source和clock_domain一起解释。

### `BoardCliRuntime.close`

源码位置：[challenge/hil/runtime_adapter.py 第 603 行](../../../challenge/hil/runtime_adapter.py#L603)。类型：`FunctionDef`。

```python
BoardCliRuntime.close(self) -> None
```

`close` 释放runtime、会话、线程或子进程资源；应在异常路径也调用，关闭成功不补齐此前缺失的trace或证据。

## 内部调用与异常路径

- `state_dict_fingerprint` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `model.state_dict`, `model.state_dict().items`, `name.encode`, `sorted`, `tensor.detach`, `tensor.detach().to`, `tensor.detach().to('cpu').contiguous`, `tensor.detach().to('cpu').contiguous().numpy`, `tensor.detach().to('cpu').contiguous().numpy().tobytes`.
- `to_dict` 调用：`list`.
- `__init__` 调用：`(self.repo_root / 'challenge').is_dir`, `AdapterError`, `CandidateIdentity`, `InterfaceRegistry`, `Path`, `Path(onnx_path).resolve`, `Path(repo_root).resolve`, `PlanValidator`, `RuntimeCapabilities`, `StudentPlanAdapter`, `StudentPlannerV0`, `StudentPreprocessor`, `_RepoModules`, `dict`, `getattr`, `git_head`, `identity_from_artifact`, `identity_from_weight_manifest`, `isinstance`, `list`, `metadata.get`, `notes.append`, `onnxruntime.InferenceSession`, `onnxruntime.SessionOptions`, `self.model.eval`, `self.model.load_state_dict`, `self.modules.get`, `self.onnx_path.is_file`, `self.session.get_inputs`, `self.session.get_modelmeta`, `self.session.get_outputs`, `sha256_file`, `shlex.split`, `state_dict_fingerprint`, `str`, `sys.path.insert`, `torch.load`, `torch.manual_seed`, `tuple`.
- `get` 调用：`AdapterError`, `__import__`, `dotted.rpartition`, `getattr`, `type`.
- `has` 调用：`self.get`.
- `infer` 调用：`AdapterError`, `RuntimeCapabilities`, `StageTrace`, `completed.stderr.strip`, `completed.stdout.strip`, `completed.stdout.strip().splitlines`, `dict`, `dict(raw_outputs).items`, `int`, `isinstance`, `json.dumps`, `json.loads`, `list`, `list(_STAGE_ORDER).index`, `outputs.items`, `payload.get`, `payload.pop`, `plan.get`, `request.get`, `rgb.numpy`, `runtime_trace.items`, `self._adapter.decode`, `self._preprocessor._rgb`, `self._preprocessor._state`, `self._preprocessor._targets`, `self._preprocessor._text`, `self._validation_scene`, `self._validator.validate`, `self.model`, `self.modules.get`, `self.session.run`, `sorted`, `state.numpy`, `str`, `subprocess.run`, `targets.numpy`, `text_tokens.numpy`, `torch.from_numpy`, `torch.inference_mode`, `trace.finish`, `trace.mark`, `type`, `validated.get`, `value.detach`, `value.detach().to`, `value.detach().to('cpu').contiguous`, `zip`.
- `verify_consistency` 调用：`StudentBackend`, `backend.infer`, `dict`, `dict(raw).items`, `isinstance`, `json.dumps`, `len`, `self._adapter.decode`, `self._preprocessor`, `self._preprocessor(request).as_tuple`, `self._torch.inference_mode`, `self._validation_scene`, `self._validator.validate`, `self.model`, `self.modules.get`, `type`, `validated.get`, `value.detach`, `value.detach().to`, `value.detach().to('cpu').contiguous`.
- `bench_model_only` 调用：`StageTrace`, `range`, `self._preprocessor`, `self.session.run`, `tensors.rgb.numpy`, `tensors.state.numpy`, `tensors.targets.numpy`, `tensors.text_tokens.numpy`, `trace.finish`, `trace.mark`, `traces.append`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 81 行：`AdapterError(f'not a carla_driving checkout: {self.repo_root}')`。
- `__init__`，第 344 行：`AdapterError(f'ONNX artifact not found: {self.onnx_path}')`。
- `__init__`，第 348 行：`AdapterError('onnxruntime is required for the ONNX chain')`。
- `__init__`，第 506 行：`AdapterError('board runtime command must not be empty')`。
- `get`，第 97 行：`AdapterError(f'cannot import {dotted}: {type(error).__name__}: {error}')`。
- `infer`，第 416 行：`AdapterError(f'ONNX inputs not produced by the preprocessor: {missing}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/identity.py](../../../challenge/hil/identity.py)
- [challenge/hil/stages.py](../../../challenge/hil/stages.py)

静态 import 消费者（含测试）：

- [challenge/hil/artifact.py](../../../challenge/hil/artifact.py)
- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/consistency.py](../../../challenge/hil/consistency.py)
- [challenge/hil/contract.py](../../../challenge/hil/contract.py)
- [challenge/hil/failure_cases.py](../../../challenge/hil/failure_cases.py)
- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/rounds.py](../../../challenge/hil/rounds.py)
- [challenge/hil/stability.py](../../../challenge/hil/stability.py)
- [challenge/hil/tests/fakes.py](../../../challenge/hil/tests/fakes.py)
- [challenge/hil/tests/test_artifact.py](../../../challenge/hil/tests/test_artifact.py)
- [challenge/hil/tests/test_contract.py](../../../challenge/hil/tests/test_contract.py)
- [challenge/hil/tests/test_provenance_and_consistency.py](../../../challenge/hil/tests/test_provenance_and_consistency.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/runtime_adapter.py`

来源 SHA256：`86e01d8bfcb87bc497b1b4102d3dd08d2602029efd7844c27b30cfe63bf66e10`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RuntimeCapabilities.full_chain` | `bool` | `无声明默认；构造/赋值方提供` |
| `RuntimeCapabilities.model_only` | `bool` | `无声明默认；构造/赋值方提供` |
| `RuntimeCapabilities.plan_validator` | `bool` | `无声明默认；构造/赋值方提供` |
| `RuntimeCapabilities.stage_source` | `str` | `无声明默认；构造/赋值方提供` |
| `RuntimeCapabilities.notes` | `tuple[str, ...]` | `()` |
| `PlannerRuntime.name` | `str` | `无声明默认；构造/赋值方提供` |
| `PlannerRuntime.identity` | `CandidateIdentity` | `无声明默认；构造/赋值方提供` |
| `PlannerRuntime.capabilities` | `RuntimeCapabilities` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_RepoModules.__init__` / 81 | `not (self.repo_root / 'challenge').is_dir()` | `raise AdapterError(f'not a carla_driving checkout: {self.repo_root}')` |
| `_RepoModules.get` / 97 | `except Exception` | `raise AdapterError(f'cannot import {dotted}: {type(error).__name__}: {error}') from error` |
| `OnnxModelRuntime.__init__` / 344 | `not self.onnx_path.is_file()` | `raise AdapterError(f'ONNX artifact not found: {self.onnx_path}')` |
| `OnnxModelRuntime.__init__` / 348 | `except ImportError` | `raise AdapterError('onnxruntime is required for the ONNX chain') from error` |
| `OnnxModelRuntime.infer` / 416 | `missing` | `raise AdapterError(f'ONNX inputs not produced by the preprocessor: {missing}')` |
| `BoardCliRuntime.__init__` / 506 | `not self.argv` | `raise AdapterError('board runtime command must not be empty')` |

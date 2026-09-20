# consistency：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/consistency.py](../../../challenge/hil/consistency.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Numerical equivalence between the torch path, the ONNX graph, and (later)

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `OutputSource.name: str`；默认：`未在声明处设置`。
- `OutputSource.identity: Mapping[str, Any]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `OutputSource`

源码位置：[challenge/hil/consistency.py 第 26 行](../../../challenge/hil/consistency.py#L26)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OutputSource.outputs`

源码位置：[challenge/hil/consistency.py 第 30 行](../../../challenge/hil/consistency.py#L30)。类型：`FunctionDef`。

```python
OutputSource.outputs(self, request: Mapping[str, Any]) -> dict[str, np.ndarray]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OutputSource.close`

源码位置：[challenge/hil/consistency.py 第 33 行](../../../challenge/hil/consistency.py#L33)。类型：`FunctionDef`。

```python
OutputSource.close(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TorchOutputSource`

源码位置：[challenge/hil/consistency.py 第 37 行](../../../challenge/hil/consistency.py#L37)。类型：`ClassDef`。

Raw ``StudentPlannerV0.forward`` outputs as numpy arrays.

### `TorchOutputSource.__init__`

源码位置：[challenge/hil/consistency.py 第 42 行](../../../challenge/hil/consistency.py#L42)。类型：`FunctionDef`。

```python
TorchOutputSource.__init__(self, repo_root: str | Path, *, weights: str | Path | None=None, seed: int | None=20260911, model_id: str=UNRESOLVED, config_id: str=UNRESOLVED) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TorchOutputSource.outputs`

源码位置：[challenge/hil/consistency.py 第 73 行](../../../challenge/hil/consistency.py#L73)。类型：`FunctionDef`。

```python
TorchOutputSource.outputs(self, request: Mapping[str, Any]) -> dict[str, np.ndarray]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TorchOutputSource.close`

源码位置：[challenge/hil/consistency.py 第 82 行](../../../challenge/hil/consistency.py#L82)。类型：`FunctionDef`。

```python
TorchOutputSource.close(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxOutputSource`

源码位置：[challenge/hil/consistency.py 第 86 行](../../../challenge/hil/consistency.py#L86)。类型：`ClassDef`。

Raw ONNX Runtime outputs; also the template for INT8-vs-FP32 checks.

### `OnnxOutputSource.__init__`

源码位置：[challenge/hil/consistency.py 第 91 行](../../../challenge/hil/consistency.py#L91)。类型：`FunctionDef`。

```python
OnnxOutputSource.__init__(self, onnx_path: str | Path, repo_root: str | Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxOutputSource.outputs`

源码位置：[challenge/hil/consistency.py 第 115 行](../../../challenge/hil/consistency.py#L115)。类型：`FunctionDef`。

```python
OnnxOutputSource.outputs(self, request: Mapping[str, Any]) -> dict[str, np.ndarray]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxOutputSource.close`

源码位置：[challenge/hil/consistency.py 第 132 行](../../../challenge/hil/consistency.py#L132)。类型：`FunctionDef`。

```python
OnnxOutputSource.close(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `compare_outputs`

源码位置：[challenge/hil/consistency.py 第 136 行](../../../challenge/hil/consistency.py#L136)。类型：`FunctionDef`。

```python
compare_outputs(reference: Mapping[str, np.ndarray], candidate: Mapping[str, np.ndarray], *, rtol: float=DEFAULT_RTOL, atol: float=DEFAULT_ATOL) -> dict[str, Any]
```

Compare every output tensor; missing or extra keys are failures.

### `compare_sources`

源码位置：[challenge/hil/consistency.py 第 179 行](../../../challenge/hil/consistency.py#L179)。类型：`FunctionDef`。

```python
compare_sources(reference: OutputSource, candidate: OutputSource, requests: Sequence[Mapping[str, Any]], *, rtol: float=DEFAULT_RTOL, atol: float=DEFAULT_ATOL) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `compare_outputs` 调用：`bool`, `delta.max`, `delta.mean`, `float`, `list`, `max`, `np.abs`, `np.allclose`, `np.asarray`, `set`, `sorted`.
- `compare_sources` 调用：`candidate.outputs`, `cases.append`, `compare_outputs`, `comparison['per_output'].items`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `dict`, `enumerate`, `isinstance`, `item.get`, `len`, `max`, `reference.outputs`, `request.get`, `sorted`, `type`.
- `__init__` 调用：`AdapterError`, `Path`, `Path(onnx_path).resolve`, `StudentPlannerV0`, `StudentPlannerV0().eval`, `StudentPreprocessor`, `_RepoModules`, `dict`, `getattr`, `metadata.get`, `modules.get`, `onnxruntime.InferenceSession`, `self.model.load_state_dict`, `self.path.is_file`, `self.session.get_inputs`, `self.session.get_modelmeta`, `self.session.get_outputs`, `sha256_file`, `str`, `torch.load`, `torch.manual_seed`.
- `outputs` 调用：`AdapterError`, `dict`, `dict(raw).items`, `np.asarray`, `self._preprocessor`, `self._torch.inference_mode`, `self.model`, `self.session.run`, `tensors.as_tuple`, `tensors.rgb.numpy`, `tensors.state.numpy`, `tensors.targets.numpy`, `tensors.text_tokens.numpy`, `value.detach`, `value.detach().to`, `value.detach().to('cpu').numpy`, `value.detach().to('cpu').numpy().astype`, `zip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 94 行：`AdapterError(f'ONNX artifact not found: {self.path}')`。
- `__init__`，第 98 行：`AdapterError('onnxruntime is required')`。
- `outputs`，第 125 行：`AdapterError(f'ONNX inputs not produced by the preprocessor: {missing}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/identity.py](../../../challenge/hil/identity.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/tests/test_provenance_and_consistency.py](../../../challenge/hil/tests/test_provenance_and_consistency.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/consistency.py`

来源 SHA256：`23caab1c54e17bb8bbe812e9ff0e11bab5e2a21c11bab979851b05f2a6ac75cd`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `OutputSource.name` | `str` | `无声明默认；构造/赋值方提供` |
| `OutputSource.identity` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `OnnxOutputSource.__init__` / 94 | `not self.path.is_file()` | `raise AdapterError(f'ONNX artifact not found: {self.path}')` |
| `OnnxOutputSource.__init__` / 98 | `except ImportError` | `raise AdapterError('onnxruntime is required') from error` |
| `OnnxOutputSource.outputs` / 125 | `missing` | `raise AdapterError(f'ONNX inputs not produced by the preprocessor: {missing}')` |

# preprocess：功能记录

上级模块：[模块说明](../modules/challenge-structure.md) · 实现：[challenge/student/preprocess.py](../../../challenge/student/preprocess.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [预处理真实变换与信息损失](student-preprocessing.md)

## 功能职责与范围

Deterministic fixed-shape preprocessing for ModelRequest V1.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `TensorizedRequest.rgb: Tensor`；默认：`未在声明处设置`。
- `TensorizedRequest.text_tokens: Tensor`；默认：`未在声明处设置`。
- `TensorizedRequest.targets: Tensor`；默认：`未在声明处设置`。
- `TensorizedRequest.state: Tensor`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `TensorizedRequest`

源码位置：[challenge/student/preprocess.py 第 32 行](../../../challenge/student/preprocess.py#L32)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TensorizedRequest.as_tuple`

源码位置：[challenge/student/preprocess.py 第 38 行](../../../challenge/student/preprocess.py#L38)。类型：`FunctionDef`。

```python
TensorizedRequest.as_tuple(self) -> tuple[Tensor, Tensor, Tensor, Tensor]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPreprocessor`

源码位置：[challenge/student/preprocess.py 第 42 行](../../../challenge/student/preprocess.py#L42)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPreprocessor.__init__`

源码位置：[challenge/student/preprocess.py 第 43 行](../../../challenge/student/preprocess.py#L43)。类型：`FunctionDef`。

```python
StudentPreprocessor.__init__(self, contract: StudentShapeContract | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPreprocessor.__call__`

源码位置：[challenge/student/preprocess.py 第 46 行](../../../challenge/student/preprocess.py#L46)。类型：`FunctionDef`。

```python
StudentPreprocessor.__call__(self, request: Mapping[str, Any]) -> TensorizedRequest
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPreprocessor._rgb`

源码位置：[challenge/student/preprocess.py 第 54 行](../../../challenge/student/preprocess.py#L54)。类型：`FunctionDef`。

```python
StudentPreprocessor._rgb(self, reference: object) -> Tensor
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPreprocessor._text`

源码位置：[challenge/student/preprocess.py 第 84 行](../../../challenge/student/preprocess.py#L84)。类型：`FunctionDef`。

```python
StudentPreprocessor._text(self, text: str) -> Tensor
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPreprocessor._targets`

源码位置：[challenge/student/preprocess.py 第 90 行](../../../challenge/student/preprocess.py#L90)。类型：`FunctionDef`。

```python
StudentPreprocessor._targets(self, raw_targets: object) -> Tensor
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPreprocessor._state`

源码位置：[challenge/student/preprocess.py 第 120 行](../../../challenge/student/preprocess.py#L120)。类型：`FunctionDef`。

```python
StudentPreprocessor._state(self, request: Mapping[str, Any]) -> Tensor
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_expanded_allowed_behaviors`

源码位置：[challenge/student/preprocess.py 第 177 行](../../../challenge/student/preprocess.py#L177)。类型：`FunctionDef`。

```python
_expanded_allowed_behaviors(request: Mapping[str, Any]) -> set[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_expanded_allowed_behaviors` 调用：`(request.get('command_hint') or {}).get`, `allowed.add`, `allowed.update`, `bool`, `request.get`, `set`, `str`.
- `__init__` 调用：`StudentShapeContract`.
- `__call__` 调用：`TensorizedRequest`, `request.get`, `self._rgb`, `self._state`, `self._targets`, `self._text`, `str`.
- `_rgb` 调用：`Image.new`, `Image.open`, `Path`, `bytearray`, `canvas.paste`, `canvas.tobytes`, `image.convert`, `image.thumbnail`, `isinstance`, `path.is_file`, `reference.strip`, `torch.tensor`, `torch.tensor((0.229, 0.224, 0.225), dtype=torch.float32).reshape`, `torch.tensor((0.485, 0.456, 0.406), dtype=torch.float32).reshape`, `torch.zeros`, `value.permute`, `value.permute(2, 0, 1).unsqueeze`, `value.permute(2, 0, 1).unsqueeze(0).to`, `value.permute(2, 0, 1).unsqueeze(0).to(torch.float32).div_`, `value.reshape`.
- `_text` 调用：`enumerate`, `ord`, `torch.zeros`.
- `_targets` 调用：`_CLASS_INDEX.get`, `any`, `enumerate`, `float`, `isinstance`, `max`, `min`, `str`, `str(target.get('relation', '')).lower`, `target.get`, `torch.zeros`.
- `_state` 调用：`('LEFT', 'RIGHT').index`, `('LEFT', 'RIGHT', 'STRAIGHT').index`, `_INTENTS.index`, `_RISK_INDEX.get`, `_TRAFFIC_INDEX.get`, `_expanded_allowed_behaviors`, `bool`, `capabilities.get`, `constraints.get`, `enumerate`, `float`, `hint.get`, `len`, `max`, `min`, `request.get`, `routing.get`, `safe_wait_behaviors.index`, `str`, `str(hint.get('direction') or '').upper`, `str(hint.get('intent', '')).upper`, `summary.get`, `torch.zeros`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/student/contract.py](../../../challenge/student/contract.py)

静态 import 消费者（含测试）：

- [challenge/distillation/shortcut_probe.py](../../../challenge/distillation/shortcut_probe.py)
- [challenge/planner/student_adapter.py](../../../challenge/planner/student_adapter.py)
- [challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py)
- [challenge/student/__init__.py](../../../challenge/student/__init__.py)
- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-structure.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/student/preprocess.py`

来源 SHA256：`dbf256c6f8495525025dc86bff3d461bf6387460674a50c3efdae80c3d0619c4`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `TensorizedRequest.rgb` | `Tensor` | `无声明默认；构造/赋值方提供` |
| `TensorizedRequest.text_tokens` | `Tensor` | `无声明默认；构造/赋值方提供` |
| `TensorizedRequest.targets` | `Tensor` | `无声明默认；构造/赋值方提供` |
| `TensorizedRequest.state` | `Tensor` | `无声明默认；构造/赋值方提供` |

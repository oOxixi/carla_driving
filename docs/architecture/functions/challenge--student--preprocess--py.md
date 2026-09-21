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

冻结的四路 Tensor 容器；字段顺序与 Student `forward(rgb,text_tokens,targets,state)` 一致。frozen 只阻止字段重新赋值，不使 Tensor 内容不可变。

### `TensorizedRequest.as_tuple`

源码位置：[challenge/student/preprocess.py 第 38 行](../../../challenge/student/preprocess.py#L38)。类型：`FunctionDef`。

```python
TensorizedRequest.as_tuple(self) -> tuple[Tensor, Tensor, Tensor, Tensor]
```

按 RGB、文本、目标、状态顺序返回 tuple，供 PyTorch/导出入口位置调用；不复制 Tensor、不迁移设备、不校验 shape。

### `StudentPreprocessor`

源码位置：[challenge/student/preprocess.py 第 42 行](../../../challenge/student/preprocess.py#L42)。类型：`ClassDef`。

把已通过 ModelRequest V1 校验的 Mapping 确定性编码为四路 float32 Tensor。它是特征约定而非通用数据清洗器；训练、评估和在线推理必须使用同一实现/版本。

### `StudentPreprocessor.__init__`

源码位置：[challenge/student/preprocess.py 第 43 行](../../../challenge/student/preprocess.py#L43)。类型：`FunctionDef`。

```python
StudentPreprocessor.__init__(self, contract: StudentShapeContract | None=None) -> None
```

保存给定 contract 或默认 `StudentShapeContract()`；不预加载图片、不验证非默认维度，也不设置设备。

### `StudentPreprocessor.__call__`

源码位置：[challenge/student/preprocess.py 第 46 行](../../../challenge/student/preprocess.py#L46)。类型：`FunctionDef`。

```python
StudentPreprocessor.__call__(self, request: Mapping[str, Any]) -> TensorizedRequest
```

读取 `rgb_ref/source_text/targets` 及摘要、约束、能力、routing，分别调用四个编码器后组装 `TensorizedRequest`。缺必填键直接由 Mapping 抛 KeyError；通常应由 `InterfaceRegistry.validate(model_request)` 在上游拒绝。

### `StudentPreprocessor._rgb`

源码位置：[challenge/student/preprocess.py 第 54 行](../../../challenge/student/preprocess.py#L54)。类型：`FunctionDef`。

```python
StudentPreprocessor._rgb(self, reference: object) -> Tensor
```

无有效字符串路径或文件不存在时返回 contract RGB shape 的全零 float32。有效图像转 RGB、保持比例缩放到框内、以 ImageNet 均值色 letterbox，转 `[1,3,H,W]`/0..1 后做 ImageNet mean/std 归一化；PIL 解码错误向上传播。路径是本机文件边界，不读取 URL。

### `StudentPreprocessor._text`

源码位置：[challenge/student/preprocess.py 第 84 行](../../../challenge/student/preprocess.py#L84)。类型：`FunctionDef`。

```python
StudentPreprocessor._text(self, text: str) -> Tensor
```

创建 `[1,text_length]` float32；逐字符取 Unicode code point `%65535/65535`，超长右截断、短文本补零。它不是 Qwen tokenizer，也没有词边界、attention mask 或语言归一化。

### `StudentPreprocessor._targets`

源码位置：[challenge/student/preprocess.py 第 90 行](../../../challenge/student/preprocess.py#L90)。类型：`FunctionDef`。

```python
StudentPreprocessor._targets(self, raw_targets: object) -> Tensor
```

创建 `[1,max_targets,14]`；只处理 list 前 N 个 Mapping 并保持原顺序。0..4 是类别 one-hot，5 是上限200 m的距离比例，6 是夹到±30 m/s的相对速度，7 是 confidence，8..12 是左右/中央/前/后关系词包含标志，13 表示未识别关系。类别查找区分大小写；数值下界和 confidence 不在此夹取，依赖上游 Schema。

### `StudentPreprocessor._state`

源码位置：[challenge/student/preprocess.py 第 120 行](../../../challenge/student/preprocess.py#L120)。类型：`FunctionDef`。

```python
StudentPreprocessor._state(self, request: Mapping[str, Any]) -> Tensor
```

创建 `[1,state_features]` 并写入 traffic/risk one-hot、gap/TTC/速度限制、must_stop、车道/间隙/路口能力、14类允许行为、目标数、command hint、routing disposition/score/reasons/safe-wait、返回方向与原车道状态。当前写到索引62，索引63保留为0；缩放只做上限或指定区间，输入合法性依赖 ModelRequest Schema。

### `_expanded_allowed_behaviors`

源码位置：[challenge/student/preprocess.py 第 177 行](../../../challenge/student/preprocess.py#L177)。类型：`FunctionDef`。

```python
_expanded_allowed_behaviors(request: Mapping[str, Any]) -> set[str]
```

`must_stop` 为真时强制只允许 STOP；否则把约束中的抽象 TURN/CHANGE_LANE 按 command hint direction 展开为左右具体行为，其他行为原样加入，空集合回退 HOLD。direction 在这里未 `.upper()`，因此应由上游合同保证大写；该集合同时进入 state 特征和 Planner adapter 可行性过滤。

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

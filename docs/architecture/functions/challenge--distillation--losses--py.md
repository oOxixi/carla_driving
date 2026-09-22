# losses：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/losses.py](../../../challenge/distillation/losses.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Masked, risk-weighted multi-head distillation objective.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `LossWeights.behavior: float`；默认：`2.0`。
- `LossWeights.target_pointer: float`；默认：`1.5`。
- `LossWeights.target_lane: float`；默认：`0.5`。
- `LossWeights.target_speed: float`；默认：`0.5`。
- `LossWeights.completion: float`；默认：`0.5`。
- `LossWeights.on_failure: float`；默认：`0.3`。
- `LossWeights.confidence: float`；默认：`0.2`。
- `LossWeights.replan: float`；默认：`0.2`。
- `LossWeights.plan_length: float`；默认：`0.5`。
- `LossWeights.requires_confirmation: float`；默认：`0.2`。

## 功能入口：输入、输出与实现说明

### `LossWeights`

源码位置：[challenge/distillation/losses.py 第 14 行](../../../challenge/distillation/losses.py#L14)。类型：`ClassDef`。

`LossWeights` 蒸馏训练类，封装Dataset、模型、标签、loss或错误合同；Head顺序、shape与训练身份受冻结Student契约约束。

### `LossWeights.from_mapping`

源码位置：[challenge/distillation/losses.py 第 27 行](../../../challenge/distillation/losses.py#L27)。类型：`FunctionDef`。

```python
LossWeights.from_mapping(cls, value: Mapping[str, Any] | None) -> 'LossWeights'
```

`from_mapping` 定义蒸馏训练使用的模型、Dataset、标签器、loss或错误类型；字段和Head顺序受Student contract约束，修改后必须重训并更新身份。

### `MultiHeadDistillationLoss`

源码位置：[challenge/distillation/losses.py 第 39 行](../../../challenge/distillation/losses.py#L39)。类型：`ClassDef`。

Compute hard-label losses and optional Teacher probability KL terms.

### `MultiHeadDistillationLoss.__init__`

源码位置：[challenge/distillation/losses.py 第 42 行](../../../challenge/distillation/losses.py#L42)。类型：`FunctionDef`。

```python
MultiHeadDistillationLoss.__init__(self, weights: LossWeights | None=None, *, soft_alpha: float=0.0, temperature: float=1.0, class_weights: Mapping[str, Any] | None=None) -> None
```

`__init__` 固化本对象的训练结构、配置或依赖，并执行源码中的初始一致性检查；后续批次仍必须保持shape、device、dtype和身份一致。

### `MultiHeadDistillationLoss.forward`

源码位置：[challenge/distillation/losses.py 第 76 行](../../../challenge/distillation/losses.py#L76)。类型：`FunctionDef`。

```python
MultiHeadDistillationLoss.forward(self, outputs: Mapping[str, Tensor], labels: Mapping[str, Tensor]) -> tuple[Tensor, dict[str, Tensor]]
```

`forward` 执行Student前向并按冻结Head合同返回或校验具名Tensor；训练路径还需检查shape、device、有限值和梯度，不能只看模型调用成功。

### `MultiHeadDistillationLoss._class_weight`

源码位置：[challenge/distillation/losses.py 第 153 行](../../../challenge/distillation/losses.py#L153)。类型：`FunctionDef`。

```python
MultiHeadDistillationLoss._class_weight(self, name: str, logits: Tensor) -> Tensor | None
```

`_class_weight` 计算当前批次的loss或指标分子/分母；padding、缺标签和类别权重由显式mask决定，不能把无效槽位或空分母计为正确。

### `MultiHeadDistillationLoss._mix_soft`

源码位置：[challenge/distillation/losses.py 第 164 行](../../../challenge/distillation/losses.py#L164)。类型：`FunctionDef`。

```python
MultiHeadDistillationLoss._mix_soft(self, hard_loss: Tensor, logits: Tensor, teacher_probs: Tensor | None, mask: Tensor, sample_weight: Tensor) -> Tensor
```

`_mix_soft` 计算当前批次的loss或指标分子/分母；padding、缺标签和类别权重由显式mask决定，不能把无效槽位或空分母计为正确。

### `_masked_cross_entropy`

源码位置：[challenge/distillation/losses.py 第 188 行](../../../challenge/distillation/losses.py#L188)。类型：`FunctionDef`。

```python
_masked_cross_entropy(logits: Tensor, targets: Tensor, mask: Tensor, sample_weight: Tensor, class_weight: Tensor | None=None) -> Tensor
```

`_masked_cross_entropy` 计算当前批次的loss或指标分子/分母；padding、缺标签和类别权重由显式mask决定，不能把无效槽位或空分母计为正确。

### `_masked_smooth_l1`

源码位置：[challenge/distillation/losses.py 第 204 行](../../../challenge/distillation/losses.py#L204)。类型：`FunctionDef`。

```python
_masked_smooth_l1(predicted: Tensor, target: Tensor, mask: Tensor, sample_weight: Tensor) -> Tensor
```

`_masked_smooth_l1` 计算当前批次的loss或指标分子/分母；padding、缺标签和类别权重由显式mask决定，不能把无效槽位或空分母计为正确。

### `_weighted_mean`

源码位置：[challenge/distillation/losses.py 第 216 行](../../../challenge/distillation/losses.py#L216)。类型：`FunctionDef`。

```python
_weighted_mean(values: Tensor, mask: Tensor, sample_weight: Tensor) -> Tensor
```

`_weighted_mean` 计算当前批次的loss或指标分子/分母；padding、缺标签和类别权重由显式mask决定，不能把无效槽位或空分母计为正确。

### `_weighted_vector_cross_entropy`

源码位置：[challenge/distillation/losses.py 第 229 行](../../../challenge/distillation/losses.py#L229)。类型：`FunctionDef`。

```python
_weighted_vector_cross_entropy(logits: Tensor, targets: Tensor, sample_weight: Tensor, class_weight: Tensor | None=None) -> Tensor
```

`_weighted_vector_cross_entropy` 计算当前批次的loss或指标分子/分母；padding、缺标签和类别权重由显式mask决定，不能把无效槽位或空分母计为正确。

### `_weighted_multilabel_bce`

源码位置：[challenge/distillation/losses.py 第 237 行](../../../challenge/distillation/losses.py#L237)。类型：`FunctionDef`。

```python
_weighted_multilabel_bce(logits: Tensor, targets: Tensor, sample_weight: Tensor) -> Tensor
```

`_weighted_multilabel_bce` 计算当前批次的loss或指标分子/分母；padding、缺标签和类别权重由显式mask决定，不能把无效槽位或空分母计为正确。

## 内部调用与异常路径

- `_masked_cross_entropy` 调用：`F.cross_entropy`, `F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1), weight=class_weight, reduction='none').reshape_as`, `ValueError`, `_weighted_mean`, `logits.reshape`, `targets.reshape`.
- `_masked_smooth_l1` 调用：`F.smooth_l1_loss`, `ValueError`, `_weighted_mean`.
- `_weighted_mean` 调用：`(values * effective).sum`, `ValueError`, `denominator.item`, `effective.sum`, `mask.to`, `values.sum`, `weights.unsqueeze`.
- `_weighted_vector_cross_entropy` 调用：`F.cross_entropy`, `_weighted_mean`, `torch.ones_like`.
- `_weighted_multilabel_bce` 调用：`F.binary_cross_entropy_with_logits`, `F.binary_cross_entropy_with_logits(logits, targets, reduction='none').mean`, `ValueError`, `_weighted_mean`, `torch.ones_like`.
- `from_mapping` 调用：`', '.join`, `ValueError`, `any`, `cls`, `dict`, `fields`, `float`, `getattr`, `raw.items`, `set`, `set(raw).difference`, `sorted`.
- `__init__` 调用：`', '.join`, `(tensor <= 0).any`, `LossWeights`, `ValueError`, `any`, `dict`, `float`, `raw_class_weights.items`, `self.class_weights.values`, `set`, `set(raw_class_weights).difference`, `sorted`, `super`, `super().__init__`, `torch.as_tensor`, `torch.isfinite`, `torch.isfinite(tensor).all`.
- `forward` 调用：`F.binary_cross_entropy_with_logits`, `F.smooth_l1_loss`, `_masked_cross_entropy`, `_masked_smooth_l1`, `_weighted_mean`, `_weighted_multilabel_bce`, `_weighted_vector_cross_entropy`, `components.items`, `getattr`, `labels.get`, `labels['confidence'].reshape`, `labels['requires_confirmation'].reshape`, `labels['sample_weight'].float`, `labels['step_mask'].bool`, `labels['target_speed_mask'].bool`, `outputs['confidence'].reshape`, `outputs['requires_confirmation_logits'].reshape`, `self._class_weight`, `self._mix_soft`, `sum`, `torch.ones_like`.
- `_class_weight` 调用：`ValueError`, `self.class_weights.get`, `value.numel`, `value.to`.
- `_mix_soft` 调用：`F.kl_div`, `F.kl_div(F.log_softmax(logits / temperature, dim=-1), safe_teacher, reduction='none').sum`, `F.log_softmax`, `ValueError`, `_weighted_mean`, `safe_teacher.sum`, `teacher_probs.float`, `teacher_probs.float().clamp_min`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 53 行：`ValueError('soft_alpha must be in [0, 1]')`。
- `__init__`，第 55 行：`ValueError('temperature must be positive')`。
- `__init__`，第 65 行：`ValueError('unknown class weight head(s): ' + ', '.join(sorted(unknown)))`。
- `__init__`，第 74 行：`ValueError('class weights must be finite positive vectors')`。
- `_class_weight`，第 158 行：`ValueError(f'class weights for {name!r} have {value.numel()} values; expected {logits.shape[-1]}')`。
- `_masked_cross_entropy`，第 196 行：`ValueError('masked classification tensors have incompatible shapes')`。
- `_masked_smooth_l1`，第 211 行：`ValueError('masked regression tensors have incompatible shapes')`。
- `_mix_soft`，第 175 行：`ValueError('Teacher soft probabilities must match Student logits')`。
- `_weighted_mean`，第 218 行：`ValueError('weighted loss tensors have incompatible shapes')`。
- `_weighted_multilabel_bce`，第 241 行：`ValueError('replan tensors have incompatible shapes')`。
- `from_mapping`，第 32 行：`ValueError('unknown loss weight(s): ' + ', '.join(sorted(unknown)))`。
- `from_mapping`，第 35 行：`ValueError('loss weights must be non-negative')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/distillation/ablation_eval.py](../../../challenge/distillation/ablation_eval.py)
- [challenge/distillation/tests/test_a1_integration.py](../../../challenge/distillation/tests/test_a1_integration.py)
- [challenge/distillation/tests/test_evaluate_class_metrics.py](../../../challenge/distillation/tests/test_evaluate_class_metrics.py)
- [challenge/distillation/tests/test_losses.py](../../../challenge/distillation/tests/test_losses.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/losses.py`

来源 SHA256：`8d514eb5df2f2cb30200e39697fbbaf5fe57323b663b4df69441a4178502e4ee`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `LossWeights.behavior` | `float` | `2.0` |
| `LossWeights.target_pointer` | `float` | `1.5` |
| `LossWeights.target_lane` | `float` | `0.5` |
| `LossWeights.target_speed` | `float` | `0.5` |
| `LossWeights.completion` | `float` | `0.5` |
| `LossWeights.on_failure` | `float` | `0.3` |
| `LossWeights.confidence` | `float` | `0.2` |
| `LossWeights.replan` | `float` | `0.2` |
| `LossWeights.plan_length` | `float` | `0.5` |
| `LossWeights.requires_confirmation` | `float` | `0.2` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `LossWeights.from_mapping` / 32 | `unknown` | `raise ValueError('unknown loss weight(s): ' + ', '.join(sorted(unknown)))` |
| `LossWeights.from_mapping` / 35 | `any((getattr(result, name) < 0.0 for name in names))` | `raise ValueError('loss weights must be non-negative')` |
| `MultiHeadDistillationLoss.__init__` / 53 | `not 0.0 <= float(soft_alpha) <= 1.0` | `raise ValueError('soft_alpha must be in [0, 1]')` |
| `MultiHeadDistillationLoss.__init__` / 55 | `float(temperature) <= 0.0` | `raise ValueError('temperature must be positive')` |
| `MultiHeadDistillationLoss.__init__` / 65 | `unknown` | `raise ValueError('unknown class weight head(s): ' + ', '.join(sorted(unknown)))` |
| `MultiHeadDistillationLoss.__init__` / 74 | `any((tensor.ndim != 1 or not torch.isfinite(tensor).all() or (tensor <= 0).any() for tensor in self.class_weights.values()))` | `raise ValueError('class weights must be finite positive vectors')` |
| `MultiHeadDistillationLoss._class_weight` / 158 | `value.numel() != logits.shape[-1]` | `raise ValueError(f'class weights for {name!r} have {value.numel()} values; expected {logits.shape[-1]}')` |
| `MultiHeadDistillationLoss._mix_soft` / 175 | `teacher_probs.shape != logits.shape` | `raise ValueError('Teacher soft probabilities must match Student logits')` |
| `_masked_cross_entropy` / 196 | `logits.shape[:-1] != targets.shape or targets.shape != mask.shape` | `raise ValueError('masked classification tensors have incompatible shapes')` |
| `_masked_smooth_l1` / 211 | `predicted.shape != target.shape or target.shape != mask.shape` | `raise ValueError('masked regression tensors have incompatible shapes')` |
| `_weighted_mean` / 218 | `values.shape != mask.shape or values.shape[0] != sample_weight.shape[0]` | `raise ValueError('weighted loss tensors have incompatible shapes')` |
| `_weighted_multilabel_bce` / 241 | `logits.shape != targets.shape` | `raise ValueError('replan tensors have incompatible shapes')` |

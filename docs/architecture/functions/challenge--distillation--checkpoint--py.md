# checkpoint：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/checkpoint.py](../../../challenge/distillation/checkpoint.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Reproducible checkpoint save/resume helpers.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `save_checkpoint`

源码位置：[challenge/distillation/checkpoint.py 第 13 行](../../../challenge/distillation/checkpoint.py#L13)。类型：`FunctionDef`。

```python
save_checkpoint(path: str | Path, *, model: torch.nn.Module, optimizer: torch.optim.Optimizer, epoch: int, global_step: int, best_metric: float, metadata: Mapping[str, Any], scheduler: Any=None, extra_state: Mapping[str, Any] | None=None) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_checkpoint`

源码位置：[challenge/distillation/checkpoint.py 第 49 行](../../../challenge/distillation/checkpoint.py#L49)。类型：`FunctionDef`。

```python
load_checkpoint(path: str | Path, *, model: torch.nn.Module, optimizer: torch.optim.Optimizer | None=None, scheduler: Any=None, map_location: str | torch.device='cpu') -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sha256_file`

源码位置：[challenge/distillation/checkpoint.py 第 78 行](../../../challenge/distillation/checkpoint.py#L78)。类型：`FunctionDef`。

```python
sha256_file(path: str | Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `save_checkpoint` 调用：`Path`, `destination.parent.mkdir`, `destination.with_name`, `dict`, `float`, `int`, `model.state_dict`, `optimizer.state_dict`, `random.getstate`, `scheduler.state_dict`, `temporary.replace`, `torch.cuda.get_rng_state_all`, `torch.cuda.is_available`, `torch.get_rng_state`, `torch.save`.
- `load_checkpoint` 调用：`Path`, `ValueError`, `model.load_state_dict`, `optimizer.load_state_dict`, `payload.get`, `random.setstate`, `rng.get`, `rng['torch'].cpu`, `scheduler.load_state_dict`, `state.cpu`, `torch.cuda.is_available`, `torch.cuda.set_rng_state_all`, `torch.load`, `torch.set_rng_state`.
- `sha256_file` 调用：`Path`, `Path(path).open`, `digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `stream.read`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `load_checkpoint`，第 60 行：`ValueError('unsupported checkpoint format')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/distillation/ablation_eval.py](../../../challenge/distillation/ablation_eval.py)
- [challenge/distillation/tests/test_checkpoint.py](../../../challenge/distillation/tests/test_checkpoint.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/checkpoint.py`

来源 SHA256：`edf3d3417f3e29a7af2ab313f7c3ebf021e12ece57885a35c22862a36f3abb72`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `load_checkpoint` / 60 | `payload.get('format_version') != 1` | `raise ValueError('unsupported checkpoint format')` |

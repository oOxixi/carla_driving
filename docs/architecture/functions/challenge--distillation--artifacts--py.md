# artifacts：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/artifacts.py](../../../challenge/distillation/artifacts.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

A3 Student weight artifacts and fail-closed FP32 promotion gate.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `export_candidate_weights`

源码位置：[challenge/distillation/artifacts.py 第 39 行](../../../challenge/distillation/artifacts.py#L39)。类型：`FunctionDef`。

```python
export_candidate_weights(output_directory: str | Path, *, model: torch.nn.Module, identity: Mapping[str, Any], validation: Mapping[str, Any], checkpoint_sha256: str) -> dict[str, Any]
```

Write a pure state_dict plus a non-promoted provenance manifest.

### `promote_fp32_candidate`

源码位置：[challenge/distillation/artifacts.py 第 83 行](../../../challenge/distillation/artifacts.py#L83)。类型：`FunctionDef`。

```python
promote_fp32_candidate(candidate_manifest: Mapping[str, Any], *, weights_path: str | Path, teacher_evaluation: Mapping[str, Any], student_evaluation: Mapping[str, Any], output_path: str | Path, max_core_drop: float=0.015, max_safety_drop: float=0.0, core_metrics: Sequence[str]=CORE_METRICS, safety_metrics: Sequence[str]=SAFETY_METRICS) -> dict[str, Any]
```

Promote only independent Validation evidence; frozen Test is forbidden.

### `_validate_evaluation_identity`

源码位置：[challenge/distillation/artifacts.py 第 158 行](../../../challenge/distillation/artifacts.py#L158)。类型：`FunctionDef`。

```python
_validate_evaluation_identity(candidate: Mapping[str, Any], evaluation: Mapping[str, Any], label: str) -> None
```

`_validate_evaluation_identity` 核对训练输入、冻结身份或候选证据；只覆盖显式检查项，不能用通过结果替代Student权重、样本清单和Teacher provenance的完整绑定。

### `_validate_pinned_teacher_candidate`

源码位置：[challenge/distillation/artifacts.py 第 191 行](../../../challenge/distillation/artifacts.py#L191)。类型：`FunctionDef`。

```python
_validate_pinned_teacher_candidate(candidate: Mapping[str, Any]) -> None
```

`_validate_pinned_teacher_candidate` 核对训练输入、冻结身份或候选证据；只覆盖显式检查项，不能用通过结果替代Student权重、样本清单和Teacher provenance的完整绑定。

### `_validate_formal_evaluation_pair`

源码位置：[challenge/distillation/artifacts.py 第 225 行](../../../challenge/distillation/artifacts.py#L225)。类型：`FunctionDef`。

```python
_validate_formal_evaluation_pair(candidate: Mapping[str, Any], teacher: Mapping[str, Any], student: Mapping[str, Any]) -> None
```

只对 `signed_d2_release_formal` 生效：强制两份评价绑定candidate的release/view SHA、相同的B2 benchmark/policy SHA、case-set digest、evaluator Git SHA与正样本数，逐端绑定predictions SHA，并要求Student评价绑定实际候选权重SHA；不读取或放行Frozen Test。

### `_require_hex`

源码位置：[challenge/distillation/artifacts.py 第 268 行](../../../challenge/distillation/artifacts.py#L268)。类型：`FunctionDef`。

```python
_require_hex(value: str, length: int, message: str) -> None
```

验证固定长度十六进制身份；失败使用调用方提供的字段级错误信息，避免把缺失SHA静默当成空身份。

### `_metrics`

源码位置：[challenge/distillation/artifacts.py 第 275 行](../../../challenge/distillation/artifacts.py#L275)。类型：`FunctionDef`。

```python
_metrics(evaluation: Mapping[str, Any], label: str) -> Mapping[str, Any]
```

`_metrics` 计算当前批次的loss或指标分子/分母；padding、缺标签和类别权重由显式mask决定，不能把无效槽位或空分母计为正确。

### `_drop_check`

源码位置：[challenge/distillation/artifacts.py 第 282 行](../../../challenge/distillation/artifacts.py#L282)。类型：`FunctionDef`。

```python
_drop_check(name: str, teacher: Mapping[str, Any], student: Mapping[str, Any], max_drop: float, group: str) -> dict[str, Any]
```

`_drop_check` 核对训练输入、冻结身份或候选证据；只覆盖显式检查项，不能用通过结果替代Student权重、样本清单和Teacher provenance的完整绑定。

### `_write_json`

源码位置：[challenge/distillation/artifacts.py 第 314 行](../../../challenge/distillation/artifacts.py#L314)。类型：`FunctionDef`。

```python
_write_json(path: Path, value: Mapping[str, Any]) -> None
```

`_write_json` 写出训练报告、checkpoint、hard-case或纯权重候选；写盘成功不代表候选可部署，仍需SHA、manifest和独立Gate绑定。

### `_json_safe`

源码位置：[challenge/distillation/artifacts.py 第 324 行](../../../challenge/distillation/artifacts.py#L324)。类型：`FunctionDef`。

```python
_json_safe(value: Any) -> Any
```

`_json_safe` 实现Dataset、批处理、过滤或报告辅助转换；它保留训练语义但不单独完成发布完整性、身份或泛化门禁。

### `_sha256`

源码位置：[challenge/distillation/artifacts.py 第 334 行](../../../challenge/distillation/artifacts.py#L334)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

`_sha256` 核对训练输入、冻结身份或候选证据；只覆盖显式检查项，不能用通过结果替代Student权重、样本清单和Teacher provenance的完整绑定。

## 内部调用与异常路径

- `export_candidate_weights` 调用：`Path`, `_sha256`, `_write_json`, `bool`, `dict`, `identity.get`, `model.state_dict`, `root.mkdir`, `str`, `temporary.replace`, `torch.save`, `weights_path.with_name`.
- `promote_fp32_candidate` 调用：`Path`, `ValueError`, `_drop_check`, `_metrics`, `_sha256`, `_validate_evaluation_identity`, `_validate_formal_evaluation_pair`, `_validate_pinned_teacher_candidate`, `_write_json`, `all`, `bool`, `candidate_manifest.get`, `checks.append`, `dict`, `float`, `student_evaluation.get`, `teacher_evaluation.get`.
- `_validate_evaluation_identity` 调用：`ValueError`, `candidate.get`, `evaluation.get`, `is_protected_split`, `split.strip`, `split.strip().lower`, `str`, `str(evaluation.get('evaluation_id', '')).strip`.
- `_validate_pinned_teacher_candidate` 调用：`ValueError`, `_require_hex`, `candidate.get`, `str`.
- `_validate_formal_evaluation_pair` 调用：`ValueError`, `_require_hex`, `candidate.get`, `evaluation.get`, `isinstance`, `str`.
- `_require_hex` 调用：`ValueError`, `any`, `len`, `value.lower`.
- `_metrics` 调用：`ValueError`, `evaluation.get`, `isinstance`.
- `_drop_check` 调用：`ValueError`, `float`, `math.isfinite`.
- `_write_json` 调用：`_json_safe`, `dict`, `json.dumps`, `path.parent.mkdir`, `path.with_name`, `temporary.replace`, `temporary.write_text`.
- `_json_safe` 调用：`_json_safe`, `isinstance`, `math.isfinite`, `str`, `value.items`.
- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `promote_fp32_candidate`：拒绝非 `PENDING_A3_FP32_GATE`、脏工作区来源、权重SHA不一致、非法drop阈值或非数值schema validity。
- `_validate_evaluation_identity`：拒绝Test/Frozen split、dataset身份不一致、空evaluation ID、Student身份错配；正式路径还拒绝非Teacher v4评价。
- `_validate_pinned_teacher_candidate`：拒绝未知/Smoke policy、非法revision/fingerprint；`frozen_manifest`要求完整Teacher Git SHA，signed D2要求固定多cohort标识及release/view SHA。
- `_validate_formal_evaluation_pair`：拒绝release/view不匹配、benchmark/policy/case-set/evaluator/predictions身份非法、成对口径不一致、样本数非正整数及Student权重SHA不匹配。
- `_metrics` 与 `_drop_check`：拒绝缺失、非数值、非有限或超出 `[0,1]` 的门禁指标。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/preflight.py](../../../challenge/distillation/preflight.py)

静态 import 消费者（含测试）：

- [challenge/distillation/promote.py](../../../challenge/distillation/promote.py)
- [challenge/distillation/tests/test_artifacts.py](../../../challenge/distillation/tests/test_artifacts.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-23 源码契约复核

基线为本次A3 promotion合同修改。以下记录signed D2多cohort路径新增的fail-closed边界；它不代表B2真实评价已完成。

### `challenge/distillation/artifacts.py`

来源 SHA256：`fbb56ef6ac338110b8164f74ca6f7bef285e4d41df5a9ec51c989e8c4d175689`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `promote_fp32_candidate` / 96 | candidate状态不是pending | 拒绝非正式待验候选 |
| `promote_fp32_candidate` / 98 | `source_worktree_dirty is not False` | 拒绝脏工作区候选 |
| `promote_fp32_candidate` / 102 | 权重实际SHA与manifest不一致 | 拒绝替换/错配权重 |
| `_validate_evaluation_identity` / 164 | Test/Frozen或非Validation别名 | 拒绝把最终测试用于A3晋级 |
| `_validate_evaluation_identity` / 175 | 正式评价不匹配冻结Teacher v4 | 拒绝历史多cohort身份冒充Gate Teacher |
| `_validate_pinned_teacher_candidate` / 193 | policy不是frozen或signed formal | 拒绝Smoke和未知identity policy |
| `_validate_pinned_teacher_candidate` / 213 | signed formal多cohort标识不匹配 | 拒绝伪造训练数据来源 |
| `_validate_formal_evaluation_pair` / 234 | evaluation的release/view与candidate不一致 | 拒绝跨数据身份评价 |
| `_validate_formal_evaluation_pair` / 254 | `sample_count`非正整数 | 拒绝空或非法分母 |
| `_validate_formal_evaluation_pair` / 262 | benchmark/policy/case/evaluator/sample两端不一致 | 拒绝Teacher/Student非同口径比较 |
| `_validate_formal_evaluation_pair` / 264 | Student权重SHA不匹配 | 拒绝评价其他checkpoint |

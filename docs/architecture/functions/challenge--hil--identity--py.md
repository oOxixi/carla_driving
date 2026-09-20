# identity：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/identity.py](../../../challenge/hil/identity.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Candidate identity (the five mandatory identifiers) and hashing helpers.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `CandidateIdentity.git_sha: str`；默认：`UNRESOLVED`。
- `CandidateIdentity.model_id: str`；默认：`UNRESOLVED`。
- `CandidateIdentity.model_sha256: str`；默认：`UNRESOLVED`。
- `CandidateIdentity.dataset_version: str`；默认：`UNRESOLVED`。
- `CandidateIdentity.config_id: str`；默认：`UNRESOLVED`。
- `CandidateIdentity.gate_status: str`；默认：`'NOT_PROVIDED'`。
- `CandidateIdentity.weights_manifest: str | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/hil/identity.py 第 26 行](../../../challenge/hil/identity.py#L26)。类型：`FunctionDef`。

```python
sha256_file(path: str | Path, chunk_size: int=1 << 20) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `git_head`

源码位置：[challenge/hil/identity.py 第 37 行](../../../challenge/hil/identity.py#L37)。类型：`FunctionDef`。

```python
git_head(repo: str | Path) -> str
```

Return the current commit SHA, or UNRESOLVED when git cannot answer.

### `CandidateIdentity`

源码位置：[challenge/hil/identity.py 第 54 行](../../../challenge/hil/identity.py#L54)。类型：`ClassDef`。

Identity of the artifact under test.

``UNRESOLVED`` is allowed so the harness can run before A2/A3 deliver; it
is never allowed to appear in a report that claims a gate result.

### `CandidateIdentity.__post_init__`

源码位置：[challenge/hil/identity.py 第 69 行](../../../challenge/hil/identity.py#L69)。类型：`FunctionDef`。

```python
CandidateIdentity.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CandidateIdentity.complete`

源码位置：[challenge/hil/identity.py 第 80 行](../../../challenge/hil/identity.py#L80)。类型：`FunctionDef`。

```python
CandidateIdentity.complete(self) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CandidateIdentity.missing`

源码位置：[challenge/hil/identity.py 第 83 行](../../../challenge/hil/identity.py#L83)。类型：`FunctionDef`。

```python
CandidateIdentity.missing(self) -> tuple[str, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CandidateIdentity.to_dict`

源码位置：[challenge/hil/identity.py 第 86 行](../../../challenge/hil/identity.py#L86)。类型：`FunctionDef`。

```python
CandidateIdentity.to_dict(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `identity_from_weight_manifest`

源码位置：[challenge/hil/identity.py 第 93 行](../../../challenge/hil/identity.py#L93)。类型：`FunctionDef`。

```python
identity_from_weight_manifest(weights: str | Path, manifest_path: str | Path) -> CandidateIdentity
```

Read A3's weight manifest and verify its digest against the real file.

The manifest's self-reported hash is never trusted: the SHA256 is recomputed
from the artifact on disk.

### `identity_from_artifact`

源码位置：[challenge/hil/identity.py 第 123 行](../../../challenge/hil/identity.py#L123)。类型：`FunctionDef`。

```python
identity_from_artifact(artifact: str | Path, *, model_id: str=UNRESOLVED, config_id: str=UNRESOLVED, dataset_version: str=UNRESOLVED, git_sha: str=UNRESOLVED) -> CandidateIdentity
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`Path`, `Path(path).open`, `digest.hexdigest`, `digest.update`, `hashlib.sha256`, `stream.read`.
- `git_head` 调用：`_SHA1_RE.fullmatch`, `completed.stdout.strip`, `str`, `subprocess.run`.
- `identity_from_weight_manifest` 调用：`CandidateIdentity`, `Path`, `Path(manifest_path).read_text`, `ValueError`, `actual.lower`, `isinstance`, `json.loads`, `manifest.get`, `reported.lower`, `sha256_file`, `str`.
- `identity_from_artifact` 调用：`CandidateIdentity`, `sha256_file`.
- `__post_init__` 调用：`ValueError`, `_SHA1_RE.fullmatch`, `getattr`, `isinstance`, `re.fullmatch`, `value.strip`.
- `complete` 调用：`all`, `getattr`.
- `missing` 调用：`getattr`, `tuple`.
- `to_dict` 调用：`asdict`, `list`, `self.missing`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 73 行：`ValueError(f'identity field {name} must be a non-empty string')`。
- `__post_init__`，第 75 行：`ValueError('git_sha must be a full 40-character Git SHA or UNRESOLVED')`。
- `__post_init__`，第 77 行：`ValueError('model_sha256 must be a 64-character hex digest or UNRESOLVED')`。
- `identity_from_weight_manifest`，第 105 行：`ValueError('weight manifest must be a JSON object')`。
- `identity_from_weight_manifest`，第 109 行：`ValueError(f'weight manifest SHA256 mismatch: manifest={reported} actual={actual}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/hil/__init__.py](../../../challenge/hil/__init__.py)
- [challenge/hil/artifact.py](../../../challenge/hil/artifact.py)
- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/consistency.py](../../../challenge/hil/consistency.py)
- [challenge/hil/freeze.py](../../../challenge/hil/freeze.py)
- [challenge/hil/provenance.py](../../../challenge/hil/provenance.py)
- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/report.py](../../../challenge/hil/report.py)
- [challenge/hil/run_io.py](../../../challenge/hil/run_io.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)
- [challenge/hil/tests/fakes.py](../../../challenge/hil/tests/fakes.py)
- [challenge/hil/tests/test_artifact.py](../../../challenge/hil/tests/test_artifact.py)
- [challenge/hil/tests/test_contract.py](../../../challenge/hil/tests/test_contract.py)
- [challenge/hil/tests/test_freeze_stability_handoff.py](../../../challenge/hil/tests/test_freeze_stability_handoff.py)
- [challenge/hil/tests/test_identity_and_io.py](../../../challenge/hil/tests/test_identity_and_io.py)
- [challenge/hil/tests/test_replay_and_failures.py](../../../challenge/hil/tests/test_replay_and_failures.py)
- [challenge/hil/tests/test_report.py](../../../challenge/hil/tests/test_report.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/identity.py`

来源 SHA256：`ad2362bfacfe7c484da977364af72841e27eb7b50830ee81ee1274ae9193f199`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `CandidateIdentity.git_sha` | `str` | `UNRESOLVED` |
| `CandidateIdentity.model_id` | `str` | `UNRESOLVED` |
| `CandidateIdentity.model_sha256` | `str` | `UNRESOLVED` |
| `CandidateIdentity.dataset_version` | `str` | `UNRESOLVED` |
| `CandidateIdentity.config_id` | `str` | `UNRESOLVED` |
| `CandidateIdentity.gate_status` | `str` | `'NOT_PROVIDED'` |
| `CandidateIdentity.weights_manifest` | `str &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `CandidateIdentity.__post_init__` / 73 | `not isinstance(value, str) or not value.strip()` | `raise ValueError(f'identity field {name} must be a non-empty string')` |
| `CandidateIdentity.__post_init__` / 75 | `self.git_sha != UNRESOLVED and (not _SHA1_RE.fullmatch(self.git_sha))` | `raise ValueError('git_sha must be a full 40-character Git SHA or UNRESOLVED')` |
| `CandidateIdentity.__post_init__` / 77 | `self.model_sha256 != UNRESOLVED and (not re.fullmatch('[0-9a-fA-F]{64}', self.model_sha256))` | `raise ValueError('model_sha256 must be a 64-character hex digest or UNRESOLVED')` |
| `identity_from_weight_manifest` / 105 | `not isinstance(manifest, Mapping)` | `raise ValueError('weight manifest must be a JSON object')` |
| `identity_from_weight_manifest` / 109 | `reported and reported.lower() != actual.lower()` | `raise ValueError(f'weight manifest SHA256 mismatch: manifest={reported} actual={actual}')` |

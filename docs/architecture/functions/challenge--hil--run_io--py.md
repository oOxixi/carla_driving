# run_io：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/run_io.py](../../../challenge/hil/run_io.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Run directory layout, atomic writers, and the per-run evidence manifest.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `new_run_id`

源码位置：[challenge/hil/run_io.py 第 16 行](../../../challenge/hil/run_io.py#L16)。类型：`FunctionDef`。

```python
new_run_id(prefix: str='b3') -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_atomic`

源码位置：[challenge/hil/run_io.py 第 21 行](../../../challenge/hil/run_io.py#L21)。类型：`FunctionDef`。

```python
_write_atomic(path: Path, text: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_json`

源码位置：[challenge/hil/run_io.py 第 28 行](../../../challenge/hil/run_io.py#L28)。类型：`FunctionDef`。

```python
write_json(path: str | Path, payload: object) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_json`

源码位置：[challenge/hil/run_io.py 第 34 行](../../../challenge/hil/run_io.py#L34)。类型：`FunctionDef`。

```python
read_json(path: str | Path) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_jsonl`

源码位置：[challenge/hil/run_io.py 第 38 行](../../../challenge/hil/run_io.py#L38)。类型：`FunctionDef`。

```python
write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_jsonl`

源码位置：[challenge/hil/run_io.py 第 49 行](../../../challenge/hil/run_io.py#L49)。类型：`FunctionDef`。

```python
read_jsonl(path: str | Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_format_cell`

源码位置：[challenge/hil/run_io.py 第 66 行](../../../challenge/hil/run_io.py#L66)。类型：`FunctionDef`。

```python
_format_cell(value: Any) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_csv`

源码位置：[challenge/hil/run_io.py 第 76 行](../../../challenge/hil/run_io.py#L76)。类型：`FunctionDef`。

```python
write_csv(path: str | Path, columns: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RunDir`

源码位置：[challenge/hil/run_io.py 第 96 行](../../../challenge/hil/run_io.py#L96)。类型：`ClassDef`。

`runs/<run_id>/` evidence root for one measurement run.

### `RunDir.__init__`

源码位置：[challenge/hil/run_io.py 第 99 行](../../../challenge/hil/run_io.py#L99)。类型：`FunctionDef`。

```python
RunDir.__init__(self, root: str | Path, run_id: str | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RunDir.path`

源码位置：[challenge/hil/run_io.py 第 107 行](../../../challenge/hil/run_io.py#L107)。类型：`FunctionDef`。

```python
RunDir.path(self, *parts: str) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RunDir.write_hardware_env`

源码位置：[challenge/hil/run_io.py 第 110 行](../../../challenge/hil/run_io.py#L110)。类型：`FunctionDef`。

```python
RunDir.write_hardware_env(self, payload: Mapping[str, Any]) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `RunDir.build_manifest`

源码位置：[challenge/hil/run_io.py 第 113 行](../../../challenge/hil/run_io.py#L113)。类型：`FunctionDef`。

```python
RunDir.build_manifest(self, *, identity: CandidateIdentity, claim_scope: str, extra: Mapping[str, Any] | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `new_run_id` 调用：`datetime.now`, `uuid4`.
- `_write_atomic` 调用：`os.replace`, `path.parent.mkdir`, `path.with_name`, `temp.write_text`.
- `write_json` 调用：`Path`, `_write_atomic`, `json.dumps`.
- `read_json` 调用：`Path`, `Path(path).read_text`, `json.loads`.
- `write_jsonl` 调用：`''.join`, `Path`, `_write_atomic`, `dict`, `json.dumps`, `target.parent.mkdir`.
- `read_jsonl` 调用：`Path`, `Path(path).open`, `TypeError`, `ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.startswith`, `raw.strip`, `records.append`.
- `_format_cell` 调用：`isinstance`, `repr`, `str`.
- `write_csv` 调用：`Path`, `ValueError`, `_format_cell`, `csv.writer`, `list`, `os.replace`, `row.get`, `set`, `sorted`, `target.parent.mkdir`, `target.with_name`, `temp.open`, `writer.writerow`.
- `__init__` 调用：`(self.root / name).mkdir`, `FileExistsError`, `Path`, `Path(root).resolve`, `new_run_id`, `self.root.exists`.
- `path` 调用：`self.root.joinpath`.
- `write_hardware_env` 调用：`dict`, `self.path`, `write_json`.
- `build_manifest` 调用：`datetime.now`, `datetime.now(timezone.utc).isoformat`, `dict`, `identity.to_dict`, `len`, `manifest.update`, `path.is_file`, `path.relative_to`, `path.relative_to(self.root).as_posix`, `path.stat`, `self.path`, `self.root.rglob`, `sha256_file`, `sorted`, `write_json`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 103 行：`FileExistsError(f'run directory already exists: {self.root}')`。
- `read_jsonl`，第 59 行：`ValueError(f'{path}:{number}: invalid JSON')`。
- `read_jsonl`，第 61 行：`TypeError(f'{path}:{number}: record must be an object')`。
- `write_csv`，第 90 行：`ValueError(f'row has columns outside the frozen schema: {sorted(unknown)}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/identity.py](../../../challenge/hil/identity.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/failure_cases.py](../../../challenge/hil/failure_cases.py)
- [challenge/hil/freeze.py](../../../challenge/hil/freeze.py)
- [challenge/hil/handoff.py](../../../challenge/hil/handoff.py)
- [challenge/hil/provenance.py](../../../challenge/hil/provenance.py)
- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/stability.py](../../../challenge/hil/stability.py)
- [challenge/hil/tests/test_identity_and_io.py](../../../challenge/hil/tests/test_identity_and_io.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/run_io.py`

来源 SHA256：`a53679482dc33547a06c3db453976a640e5c7c0fd1a4b29d4df58ae749c6257c`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 59 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{number}: invalid JSON') from error` |
| `read_jsonl` / 61 | `not isinstance(payload, dict)` | `raise TypeError(f'{path}:{number}: record must be an object')` |
| `write_csv` / 90 | `unknown` | `raise ValueError(f'row has columns outside the frozen schema: {sorted(unknown)}')` |
| `RunDir.__init__` / 103 | `self.root.exists()` | `raise FileExistsError(f'run directory already exists: {self.root}')` |

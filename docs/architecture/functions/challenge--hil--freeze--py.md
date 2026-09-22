# freeze：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/freeze.py](../../../challenge/hil/freeze.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Freeze a request set into a self-contained replay snapshot.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_canonical_sha256`

源码位置：[challenge/hil/freeze.py 第 25 行](../../../challenge/hil/freeze.py#L25)。类型：`FunctionDef`。

```python
_canonical_sha256(payload: Any) -> str
```

`_canonical_sha256` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

### `_extension`

源码位置：[challenge/hil/freeze.py 第 32 行](../../../challenge/hil/freeze.py#L32)。类型：`FunctionDef`。

```python
_extension(path: str | None) -> str
```

`_extension` 读取冻结输入、配置、图像或provenance；路径解析必须保持发布边界，缺失资源不能静默当作成功样本。

### `freeze_snapshot`

源码位置：[challenge/hil/freeze.py 第 39 行](../../../challenge/hil/freeze.py#L39)。类型：`FunctionDef`。

```python
freeze_snapshot(*, delivery_root: str | Path | None, out_root: str | Path, name: str, requests_path: str | Path | None=None, repo_root: str | Path | None=None, limit: int | None=None, copy_rgb: bool=True) -> dict[str, Any]
```

`freeze_snapshot` 写出冻结快照、handoff、trace、遥测或报告产物；文件必须绑定候选身份、输入哈希和环境，写盘成功不是Gate通过。

### `load_frozen_snapshot`

源码位置：[challenge/hil/freeze.py 第 127 行](../../../challenge/hil/freeze.py#L127)。类型：`FunctionDef`。

```python
load_frozen_snapshot(snapshot_dir: str | Path) -> tuple[list[ReplayCase], dict[str, Any]]
```

Read a snapshot back into replay cases, verifying every recorded hash.

## 内部调用与异常路径

- `_canonical_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(encoded).hexdigest`, `json.dumps`, `json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode`.
- `_extension` 调用：`Path`.
- `freeze_snapshot` 调用：`Path`, `Path(out_root).resolve`, `ValueError`, `_canonical_sha256`, `_extension`, `any`, `cases_path.stat`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `destination.exists`, `len`, `load_replay_cases`, `records.append`, `rgb_dir.mkdir`, `sha256_file`, `shutil.copyfile`, `sorted`, `str`, `sum`, `target.mkdir`, `write_json`, `write_jsonl`.
- `load_frozen_snapshot` 调用：`(root / 'manifest.json').read_text`, `Path`, `Path(snapshot_dir).resolve`, `ReplayCase`, `ValueError`, `_canonical_sha256`, `candidate.is_file`, `cases.append`, `cases_path.open`, `json.loads`, `len`, `line.strip`, `manifest.get`, `record.get`, `sha256_file`, `str`, `sum`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `freeze_snapshot`，第 50 行：`ValueError('snapshot name must be a plain directory name')`。
- `load_frozen_snapshot`，第 135 行：`ValueError(f'snapshot cases.jsonl changed: {actual} != {recorded}')`。
- `load_frozen_snapshot`，第 146 行：`ValueError(f"snapshot request drifted for {record.get('case_id')}: {digest} != {record['request_sha256']}")`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/identity.py](../../../challenge/hil/identity.py)
- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/run_io.py](../../../challenge/hil/run_io.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/tests/test_freeze_stability_handoff.py](../../../challenge/hil/tests/test_freeze_stability_handoff.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/freeze.py`

来源 SHA256：`179d9d98095a9ee5290377f4b3f4ffa63cb440ffeebc9b94038a3e23c545132e`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `freeze_snapshot` / 50 | `not name or any((character in name for character in '\\/:*?"<>&#124;'))` | `raise ValueError('snapshot name must be a plain directory name')` |
| `load_frozen_snapshot` / 135 | `recorded != actual` | `raise ValueError(f'snapshot cases.jsonl changed: {actual} != {recorded}')` |
| `load_frozen_snapshot` / 146 | `digest != record['request_sha256']` | `raise ValueError(f"snapshot request drifted for {record.get('case_id')}: {digest} != {record['request_sha256']}")` |

# handoff：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/handoff.py](../../../challenge/hil/handoff.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Export B3 runtime failures into a form A3 can actually consume.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_canonical_sha256`

源码位置：[challenge/hil/handoff.py 第 29 行](../../../challenge/hil/handoff.py#L29)。类型：`FunctionDef`。

```python
_canonical_sha256(payload: Any) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_failure_taxonomy`

源码位置：[challenge/hil/handoff.py 第 36 行](../../../challenge/hil/handoff.py#L36)。类型：`FunctionDef`。

```python
_failure_taxonomy(structural_failures: Sequence[str], outcome: str, teacher_behaviors: Sequence[str], student_behaviors: Sequence[str]) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `export_handoff`

源码位置：[challenge/hil/handoff.py 第 68 行](../../../challenge/hil/handoff.py#L68)。类型：`FunctionDef`。

```python
export_handoff(*, out_dir: str | Path, run_id: str, replay_rows: Iterable[Mapping[str, Any]], plan_rows: Iterable[Mapping[str, Any]], abnormal_summary: Mapping[str, Any] | None, source_snapshot: Mapping[str, Any] | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_taxonomy_counts`

源码位置：[challenge/hil/handoff.py 第 173 行](../../../challenge/hil/handoff.py#L173)。类型：`FunctionDef`。

```python
_taxonomy_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_readme`

源码位置：[challenge/hil/handoff.py 第 181 行](../../../challenge/hil/handoff.py#L181)。类型：`FunctionDef`。

```python
_readme(summary: Mapping[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_handoff`

源码位置：[challenge/hil/handoff.py 第 198 行](../../../challenge/hil/handoff.py#L198)。类型：`FunctionDef`。

```python
load_handoff(path: str | Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_canonical_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(encoded).hexdigest`, `json.dumps`, `json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode`.
- `_failure_taxonomy` 调用：`item.endswith`, `item.startswith`, `len`, `set`, `sorted`, `taxonomy.append`.
- `export_handoff` 调用：`(plan_row or {}).get`, `(target / 'README.md').write_text`, `Path`, `_canonical_sha256`, `_failure_taxonomy`, `_readme`, `_taxonomy_counts`, `abnormal_summary.get`, `bool`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `detail.get`, `detail_path.is_file`, `detail_path.read_text`, `dict`, `int`, `item.get`, `json.loads`, `len`, `plans_by_case.get`, `robustness.append`, `row.get`, `semantic.append`, `str`, `str(row.get('structural_failures', '')).split`, `str(row.get('student_behavior_sequence', '')).split`, `str(row.get('teacher_behavior_sequence', '')).split`, `sum`, `target.mkdir`, `write_json`, `write_jsonl`.
- `_taxonomy_counts` 调用：`counts.get`, `record.get`, `str`.
- `_readme` 调用：`'\n'.join`.
- `load_handoff` 调用：`read_jsonl`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

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

### `challenge/hil/handoff.py`

来源 SHA256：`cadbf94c168482bdffd7a049ea459625cd1c6dee0d2c62aeaf6d7e24965b4bf7`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

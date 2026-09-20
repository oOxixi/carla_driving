# provenance：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/provenance.py](../../../challenge/hil/provenance.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Provenance pins that every B3 run must carry.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `resolve_tag`

源码位置：[challenge/hil/provenance.py 第 25 行](../../../challenge/hil/provenance.py#L25)。类型：`FunctionDef`。

```python
resolve_tag(repo_root: str | Path, tag: str=TEACHER_BASELINE_TAG) -> dict[str, Any]
```

Resolve a local tag to a commit SHA without touching the network.

### `_load_pin`

源码位置：[challenge/hil/provenance.py 第 45 行](../../../challenge/hil/provenance.py#L45)。类型：`FunctionDef`。

```python
_load_pin(repo: Path, *, label: str, manifest_relative: str, default_tag: str, git_key: str, fingerprint_key: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `teacher_baselines`

源码位置：[challenge/hil/provenance.py 第 99 行](../../../challenge/hil/provenance.py#L99)。类型：`FunctionDef`。

```python
teacher_baselines(repo_root: str | Path) -> dict[str, Any]
```

Read every pinned Teacher manifest and cross-check it against its tag.

Two pins currently exist: ``teacher-baseline-v1`` (identity + contracts) and
``teacher-baseline-v4`` (data-semantic governance).  Both describe the same
model, so a run records both and asserts that their model identities agree;
recording only one would silently hide a governance change.

### `teacher_baseline`

源码位置：[challenge/hil/provenance.py 第 138 行](../../../challenge/hil/provenance.py#L138)。类型：`FunctionDef`。

```python
teacher_baseline(repo_root: str | Path) -> dict[str, Any]
```

Backwards-compatible accessor: the active pin.

## 内部调用与异常路径

- `resolve_tag` 调用：`completed.stdout.strip`, `str`, `subprocess.run`, `type`.
- `_load_pin` 调用：`manifest_path.is_file`, `payload.get`, `pin.update`, `read_json`, `resolve_tag`, `sha256_file`, `str`.
- `teacher_baselines` 调用：`Path`, `Path(repo_root).resolve`, `_load_pin`, `all`, `bool`, `len`, `list`.
- `teacher_baseline` 调用：`teacher_baselines`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/identity.py](../../../challenge/hil/identity.py)
- [challenge/hil/run_io.py](../../../challenge/hil/run_io.py)

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

### `challenge/hil/provenance.py`

来源 SHA256：`0daa5db47efaf4d60c97272f9cd0445a0d14794480fd76d72a01df1e750e9bb4`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

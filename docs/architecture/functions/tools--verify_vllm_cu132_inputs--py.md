# verify_vllm_cu132_inputs：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/verify_vllm_cu132_inputs.py](../../../tools/verify_vllm_cu132_inputs.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Verify immutable release inputs before the offline CUDA 13.2 wheel build.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_sha256`

源码位置：[tools/verify_vllm_cu132_inputs.py 第 11 行](../../../tools/verify_vllm_cu132_inputs.py#L11)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_json`

源码位置：[tools/verify_vllm_cu132_inputs.py 第 19 行](../../../tools/verify_vllm_cu132_inputs.py#L19)。类型：`FunctionDef`。

```python
_load_json(path: Path) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_source`

源码位置：[tools/verify_vllm_cu132_inputs.py 第 27 行](../../../tools/verify_vllm_cu132_inputs.py#L27)。类型：`FunctionDef`。

```python
verify_source(source: Path, lock: dict[str, object]) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_wheelhouse`

源码位置：[tools/verify_vllm_cu132_inputs.py 第 46 行](../../../tools/verify_vllm_cu132_inputs.py#L46)。类型：`FunctionDef`。

```python
verify_wheelhouse(wheelhouse: Path, lock: dict[str, object]) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/verify_vllm_cu132_inputs.py 第 79 行](../../../tools/verify_vllm_cu132_inputs.py#L79)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `_load_json` 调用：`ValueError`, `isinstance`, `json.load`, `path.open`.
- `verify_source` 调用：`ValueError`, `_sha256`, `any`, `isinstance`, `lock.get`, `source.stat`.
- `verify_wheelhouse` 调用：`ValueError`, `_sha256`, `all`, `entry.get`, `expected.items`, `isinstance`, `item.get`, `len`, `lock.get`, `path.is_file`, `path.stat`, `set`, `set(resolved).issubset`, `sum`, `wheelhouse.iterdir`.
- `main` 调用：`_load_json`, `argparse.ArgumentParser`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `result.update`, `verify_source`, `verify_wheelhouse`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_load_json`，第 23 行：`ValueError(f'{path} must contain a JSON object')`。
- `verify_source`，第 31 行：`ValueError('source lock must contain commit and source_archive')`。
- `verify_source`，第 34 行：`ValueError('source_archive lock is incomplete')`。
- `verify_source`，第 36 行：`ValueError('source archive provenance commit does not match lock commit')`。
- `verify_source`，第 38 行：`ValueError('source archive filename does not identify the locked commit')`。
- `verify_source`，第 40 行：`ValueError('source archive byte size does not match lock')`。
- `verify_source`，第 42 行：`ValueError('source archive SHA256 does not match lock')`。
- `verify_wheelhouse`，第 51 行：`ValueError('wheelhouse lock must contain files, resolved_files, and excluded_candidates')`。
- `verify_wheelhouse`，第 58 行：`ValueError('wheelhouse lock has duplicate or incomplete file entries')`。
- `verify_wheelhouse`，第 61 行：`ValueError('wheelhouse file set does not match lock')`。
- `verify_wheelhouse`，第 63 行：`ValueError('wheelhouse total byte size does not match lock')`。
- `verify_wheelhouse`，第 67 行：`ValueError(f'wheelhouse hash mismatch: {name}')`。
- `verify_wheelhouse`，第 69 行：`ValueError('resolved wheel list is invalid')`。
- `verify_wheelhouse`，第 71 行：`ValueError('excluded wheel candidates do not exactly account for wheelhouse extras')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 81 行：`parser.add_argument('--source', type=Path, required=True)`。
- 第 82 行：`parser.add_argument('--source-lock', type=Path, required=True)`。
- 第 83 行：`parser.add_argument('--wheelhouse', type=Path, required=True)`。
- 第 84 行：`parser.add_argument('--wheelhouse-lock', type=Path, required=True)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_vllm_cu132_build.py](../../../integration/tests/test_vllm_cu132_build.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/verify_vllm_cu132_inputs.py`

来源 SHA256：`8441dc5af83b41de5cd04ebf60c79d8d4f8163ffc8b2863ea33bb5eec9fbc80c`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 81 | `'--source'` | `type=Path; required=True` |
| 82 | `'--source-lock'` | `type=Path; required=True` |
| 83 | `'--wheelhouse'` | `type=Path; required=True` |
| 84 | `'--wheelhouse-lock'` | `type=Path; required=True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_load_json` / 23 | `not isinstance(value, dict)` | `raise ValueError(f'{path} must contain a JSON object')` |
| `verify_source` / 31 | `not isinstance(archive, dict) or not isinstance(commit, str)` | `raise ValueError('source lock must contain commit and source_archive')` |
| `verify_source` / 34 | `any((key not in archive for key in required))` | `raise ValueError('source_archive lock is incomplete')` |
| `verify_source` / 36 | `archive['generated_from_commit'] != commit` | `raise ValueError('source archive provenance commit does not match lock commit')` |
| `verify_source` / 38 | `source.name != archive['filename'] or commit not in source.name` | `raise ValueError('source archive filename does not identify the locked commit')` |
| `verify_source` / 40 | `source.stat().st_size != archive['bytes']` | `raise ValueError('source archive byte size does not match lock')` |
| `verify_source` / 42 | `_sha256(source) != archive['sha256']` | `raise ValueError('source archive SHA256 does not match lock')` |
| `verify_wheelhouse` / 51 | `not all((isinstance(value, list) for value in (files, resolved, excluded)))` | `raise ValueError('wheelhouse lock must contain files, resolved_files, and excluded_candidates')` |
| `verify_wheelhouse` / 58 | `len(expected) != len(files) or len(expected) != lock.get('file_count')` | `raise ValueError('wheelhouse lock has duplicate or incomplete file entries')` |
| `verify_wheelhouse` / 61 | `actual != set(expected)` | `raise ValueError('wheelhouse file set does not match lock')` |
| `verify_wheelhouse` / 63 | `sum((path.stat().st_size for path in wheelhouse.iterdir() if path.is_file())) != lock.get('total_bytes')` | `raise ValueError('wheelhouse total byte size does not match lock')` |
| `verify_wheelhouse` / 67 | `path.stat().st_size != entry.get('bytes') or _sha256(path) != entry.get('sha256')` | `raise ValueError(f'wheelhouse hash mismatch: {name}')` |
| `verify_wheelhouse` / 69 | `len(set(resolved)) != len(resolved) or not set(resolved).issubset(expected)` | `raise ValueError('resolved wheel list is invalid')` |
| `verify_wheelhouse` / 71 | `actual - set(resolved) != set(excluded)` | `raise ValueError('excluded wheel candidates do not exactly account for wheelhouse extras')` |

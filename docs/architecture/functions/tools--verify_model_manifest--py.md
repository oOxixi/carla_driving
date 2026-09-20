# verify_model_manifest：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/verify_model_manifest.py](../../../tools/verify_model_manifest.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Verify that one staged model profile exactly matches its release manifest.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[tools/verify_model_manifest.py 第 11 行](../../../tools/verify_model_manifest.py#L11)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_safe_manifest_path`

源码位置：[tools/verify_model_manifest.py 第 19 行](../../../tools/verify_model_manifest.py#L19)。类型：`FunctionDef`。

```python
_safe_manifest_path(value: object) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_profile`

源码位置：[tools/verify_model_manifest.py 第 28 行](../../../tools/verify_model_manifest.py#L28)。类型：`FunctionDef`。

```python
verify_profile(manifest_path: Path, root: Path, profile: str) -> dict[str, object]
```

Return the sole verified profile entry or raise ``ValueError`` on drift.

### `main`

源码位置：[tools/verify_model_manifest.py 第 74 行](../../../tools/verify_model_manifest.py#L74)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `_safe_manifest_path` 调用：`PurePosixPath`, `ValueError`, `candidate.as_posix`, `candidate.is_absolute`, `isinstance`.
- `verify_profile` 调用：`ValueError`, `_safe_manifest_path`, `actual.items`, `entry.get`, `isinstance`, `item.get`, `json.loads`, `len`, `manifest_path.read_text`, `metadata.get`, `path.is_file`, `path.is_symlink`, `path.relative_to`, `path.relative_to(root).as_posix`, `path.resolve`, `path.stat`, `payload.get`, `resolved.relative_to`, `root.is_dir`, `root.is_symlink`, `root.resolve`, `root.rglob`, `set`, `sha256_file`.
- `main` 调用：`argparse.ArgumentParser`, `entry.get`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `verify_profile`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_safe_manifest_path`，第 21 行：`ValueError('manifest file path must be a non-empty string')`。
- `_safe_manifest_path`，第 24 行：`ValueError(f'unsafe manifest file path: {value}')`。
- `verify_profile`，第 33 行：`ValueError('manifest models must be a list')`。
- `verify_profile`，第 36 行：`ValueError(f'manifest must contain one profile entry: {profile}')`。
- `verify_profile`，第 40 行：`ValueError(f'manifest profile files must be a list: {profile}')`。
- `verify_profile`，第 44 行：`ValueError('manifest file entry must be an object')`。
- `verify_profile`，第 47 行：`ValueError(f'duplicate manifest file entry: {relative}')`。
- `verify_profile`，第 50 行：`ValueError(f'model root does not exist: {root}')`。
- `verify_profile`，第 57 行：`ValueError('model file set does not match manifest')`。
- `verify_profile`，第 60 行：`ValueError(f'model files must not be symlinks: {relative}')`。
- `verify_profile`，第 65 行：`ValueError(f'model file escapes root: {relative}')`。
- `verify_profile`，第 68 行：`ValueError(f'byte size mismatch: {relative}')`。
- `verify_profile`，第 70 行：`ValueError(f'SHA256 mismatch: {relative}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 76 行：`parser.add_argument('--manifest', type=Path, required=True)`。
- 第 77 行：`parser.add_argument('--root', type=Path, required=True)`。
- 第 78 行：`parser.add_argument('--profile', required=True)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_model_manifest.py](../../../integration/tests/test_model_manifest.py)
- [integration/tests/test_repro_compose.py](../../../integration/tests/test_repro_compose.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/verify_model_manifest.py`

来源 SHA256：`b784d8992760d07f1449415dd29734f44ab2b337c4b1c9fb81eb48f7edb95039`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 76 | `'--manifest'` | `type=Path; required=True` |
| 77 | `'--root'` | `type=Path; required=True` |
| 78 | `'--profile'` | `required=True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_safe_manifest_path` / 21 | `not isinstance(value, str) or not value` | `raise ValueError('manifest file path must be a non-empty string')` |
| `_safe_manifest_path` / 24 | `candidate.is_absolute() or '..' in candidate.parts or '\\' in value` | `raise ValueError(f'unsafe manifest file path: {value}')` |
| `verify_profile` / 33 | `not isinstance(models, list)` | `raise ValueError('manifest models must be a list')` |
| `verify_profile` / 36 | `len(matches) != 1` | `raise ValueError(f'manifest must contain one profile entry: {profile}')` |
| `verify_profile` / 40 | `not isinstance(files, list)` | `raise ValueError(f'manifest profile files must be a list: {profile}')` |
| `verify_profile` / 44 | `not isinstance(item, dict)` | `raise ValueError('manifest file entry must be an object')` |
| `verify_profile` / 47 | `relative in expected` | `raise ValueError(f'duplicate manifest file entry: {relative}')` |
| `verify_profile` / 50 | `root.is_symlink() or not root.is_dir()` | `raise ValueError(f'model root does not exist: {root}')` |
| `verify_profile` / 57 | `set(actual) != set(expected)` | `raise ValueError('model file set does not match manifest')` |
| `verify_profile` / 60 | `path.is_symlink()` | `raise ValueError(f'model files must not be symlinks: {relative}')` |
| `verify_profile` / 65 | `except ValueError` | `raise ValueError(f'model file escapes root: {relative}') from exc` |
| `verify_profile` / 68 | `path.stat().st_size != metadata.get('bytes')` | `raise ValueError(f'byte size mismatch: {relative}')` |
| `verify_profile` / 70 | `sha256_file(path) != metadata.get('sha256')` | `raise ValueError(f'SHA256 mismatch: {relative}')` |

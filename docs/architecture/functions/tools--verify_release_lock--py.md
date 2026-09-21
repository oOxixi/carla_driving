# verify_release_lock：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/verify_release_lock.py](../../../tools/verify_release_lock.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Verify one hashed staged release asset before it is consumed by a build.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[tools/verify_release_lock.py 第 10 行](../../../tools/verify_release_lock.py#L10)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_asset`

源码位置：[tools/verify_release_lock.py 第 18 行](../../../tools/verify_release_lock.py#L18)。类型：`FunctionDef`。

```python
verify_asset(lock_path: Path, root: Path, key: str) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/verify_release_lock.py 第 30 行](../../../tools/verify_release_lock.py#L30)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `verify_asset` 调用：`ValueError`, `json.loads`, `lock_path.read_text`, `path.is_file`, `path.stat`, `sha256_file`.
- `main` 调用：`argparse.ArgumentParser`, `parser.add_argument`, `parser.parse_args`, `print`, `verify_asset`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `verify_asset`，第 22 行：`ValueError(f'locked asset is missing: {path}')`。
- `verify_asset`，第 24 行：`ValueError(f'locked asset byte size mismatch: {path.name}')`。
- `verify_asset`，第 26 行：`ValueError(f'locked asset SHA256 mismatch: {path.name}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 32 行：`parser.add_argument('--lock', type=Path, required=True)`。
- 第 33 行：`parser.add_argument('--root', type=Path, required=True)`。
- 第 34 行：`parser.add_argument('--key', required=True)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_model_manifest.py](../../../integration/tests/test_model_manifest.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/verify_release_lock.py`

来源 SHA256：`08eff5605027d8f0ef548e890ccf0f110653cc69a6432440a4af3be86f778424`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 32 | `'--lock'` | `type=Path; required=True` |
| 33 | `'--root'` | `type=Path; required=True` |
| 34 | `'--key'` | `required=True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `verify_asset` / 22 | `not path.is_file()` | `raise ValueError(f'locked asset is missing: {path}')` |
| `verify_asset` / 24 | `path.stat().st_size != metadata['bytes']` | `raise ValueError(f'locked asset byte size mismatch: {path.name}')` |
| `verify_asset` / 26 | `sha256_file(path) != metadata['sha256']` | `raise ValueError(f'locked asset SHA256 mismatch: {path.name}')` |

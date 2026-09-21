# promote_reference_run：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/promote_reference_run.py](../../../tools/promote_reference_run.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Promote one completed, hash-verified runtime directory to reference evidence.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_sha256`

源码位置：[tools/promote_reference_run.py 第 17 行](../../../tools/promote_reference_run.py#L17)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `promote_reference_run`

源码位置：[tools/promote_reference_run.py 第 21 行](../../../tools/promote_reference_run.py#L21)。类型：`FunctionDef`。

```python
promote_reference_run(source: Path, destination: Path, hardware_label: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/promote_reference_run.py 第 49 行](../../../tools/promote_reference_run.py#L49)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_sha256` 调用：`frozen_text_sha256`.
- `promote_reference_run` 调用：`', '.join`, `(source / name).exists`, `FileExistsError`, `FileNotFoundError`, `ValueError`, `_sha256`, `destination.exists`, `json.loads`, `manifest.get`, `manifest.get('files', {}).items`, `manifest_path.is_file`, `manifest_path.read_text`, `path.is_file`, `readme.is_file`, `readme.read_text`, `readme.write_text`, `shutil.copytree`.
- `main` 调用：`argparse.ArgumentParser`, `parser.add_argument`, `parser.parse_args`, `promote_reference_run`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `promote_reference_run`，第 24 行：`FileNotFoundError(f'run manifest missing: {manifest_path}')`。
- `promote_reference_run`，第 27 行：`ValueError('cannot promote a RUNNING manifest')`。
- `promote_reference_run`，第 31 行：`FileNotFoundError('incomplete run evidence: ' + ', '.join(missing))`。
- `promote_reference_run`，第 35 行：`FileNotFoundError(f'manifest evidence missing: {relative}')`。
- `promote_reference_run`，第 37 行：`ValueError(f'manifest hash mismatch: {relative}')`。
- `promote_reference_run`，第 39 行：`FileExistsError(f'reference destination already exists: {destination}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 51 行：`parser.add_argument('--run-dir', type=Path, required=True)`。
- 第 52 行：`parser.add_argument('--destination', type=Path, required=True)`。
- 第 53 行：`parser.add_argument('--hardware-label', required=True)`。

## 上下游与关联验证

静态导入的项目内实现：

- [tools/frozen_text_hash.py](../../../tools/frozen_text_hash.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/promote_reference_run.py`

来源 SHA256：`351e7bcfa35c0534620c0919aeb83f4f04547c501131622a22d5ee3d66b21bfe`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 51 | `'--run-dir'` | `type=Path; required=True` |
| 52 | `'--destination'` | `type=Path; required=True` |
| 53 | `'--hardware-label'` | `required=True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `promote_reference_run` / 24 | `not manifest_path.is_file()` | `raise FileNotFoundError(f'run manifest missing: {manifest_path}')` |
| `promote_reference_run` / 27 | `manifest.get('status') == 'RUNNING'` | `raise ValueError('cannot promote a RUNNING manifest')` |
| `promote_reference_run` / 31 | `missing` | `raise FileNotFoundError('incomplete run evidence: ' + ', '.join(missing))` |
| `promote_reference_run` / 35 | `not path.is_file()` | `raise FileNotFoundError(f'manifest evidence missing: {relative}')` |
| `promote_reference_run` / 37 | `_sha256(path) != expected` | `raise ValueError(f'manifest hash mismatch: {relative}')` |
| `promote_reference_run` / 39 | `destination.exists()` | `raise FileExistsError(f'reference destination already exists: {destination}')` |

# generate_wheelhouse_lock：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/generate_wheelhouse_lock.py](../../../tools/generate_wheelhouse_lock.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Turn one pip --report result into a strict wheelhouse manifest and hash lock.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[tools/generate_wheelhouse_lock.py 第 11 行](../../../tools/generate_wheelhouse_lock.py#L11)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

【sha256_file】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `main`

源码位置：[tools/generate_wheelhouse_lock.py 第 19 行](../../../tools/generate_wheelhouse_lock.py#L19)。类型：`FunctionDef`。

```python
main() -> int
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `sha256_file` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `main` 调用：`'\n'.join`, `Path`, `ValueError`, `argparse.ArgumentParser`, `args.lock.write_text`, `args.report.read_text`, `args.requirements_lock.write_text`, `args.wheelhouse.resolve`, `by_name.get`, `item['name'].lower`, `json.dumps`, `json.loads`, `len`, `parser.add_argument`, `parser.parse_args`, `path.is_file`, `path.stat`, `resolved.append`, `root.iterdir`, `sha256_file`, `sorted`, `unquote`, `urlparse`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 37 行：`ValueError(f'report wheel is absent from wheelhouse: {filename}')`。
- `main`，第 40 行：`ValueError('resolver selected duplicate project names')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 21 行：`parser.add_argument('--report', type=Path, required=True)`。
- 第 22 行：`parser.add_argument('--wheelhouse', type=Path, required=True)`。
- 第 23 行：`parser.add_argument('--lock', type=Path, required=True)`。
- 第 24 行：`parser.add_argument('--requirements-lock', type=Path, required=True)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/generate_wheelhouse_lock.py`

来源 SHA256：`077013a4e7334d4b0dae993c61f31fd8caecff476d920fca4e67acd9a41a046d`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 21 | `'--report'` | `type=Path; required=True` |
| 22 | `'--wheelhouse'` | `type=Path; required=True` |
| 23 | `'--lock'` | `type=Path; required=True` |
| 24 | `'--requirements-lock'` | `type=Path; required=True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 37 | `wheel is None` | `raise ValueError(f'report wheel is absent from wheelhouse: {filename}')` |
| `main` / 40 | `len({item['name'].lower() for item in resolved}) != len(resolved)` | `raise ValueError('resolver selected duplicate project names')` |

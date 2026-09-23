# verify_wheelhouse_lock：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/verify_wheelhouse_lock.py](../../../tools/verify_wheelhouse_lock.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Reject any wheelhouse drift from its frozen complete manifest.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `verify_wheelhouse`

源码位置：[tools/verify_wheelhouse_lock.py 第 11 行](../../../tools/verify_wheelhouse_lock.py#L11)。类型：`FunctionDef`。

```python
verify_wheelhouse(lock_path: Path, root: Path, suffix: str='.whl') -> None
```

【verify_wheelhouse】检查维护工具的数据检查、生成、评测或证据处理的局部合同并返回/累计函数体定义的结果；静态校验通过不等于外部服务、CARLA、音频模型或最终交付已经通过。

### `main`

源码位置：[tools/verify_wheelhouse_lock.py 第 23 行](../../../tools/verify_wheelhouse_lock.py#L23)。类型：`FunctionDef`。

```python
main() -> int
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `verify_wheelhouse` 调用：`ValueError`, `actual.items`, `json.loads`, `lock_path.read_text`, `path.is_file`, `path.name.endswith`, `path.stat`, `root.iterdir`, `set`, `sha256_file`.
- `main` 调用：`argparse.ArgumentParser`, `parser.add_argument`, `parser.parse_args`, `verify_wheelhouse`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `verify_wheelhouse`，第 16 行：`ValueError('wheelhouse file set does not match lock')`。
- `verify_wheelhouse`，第 20 行：`ValueError(f'wheelhouse hash mismatch: {name}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 25 行：`parser.add_argument('--lock', type=Path, required=True)`。
- 第 26 行：`parser.add_argument('--wheelhouse', type=Path, required=True)`。
- 第 27 行：`parser.add_argument('--suffix', default='.whl')`。

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

### `tools/verify_wheelhouse_lock.py`

来源 SHA256：`6fac93c45f2ee98e19fea91becd8bac9726df7bf4c79adce675db7082ceecc90`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 25 | `'--lock'` | `type=Path; required=True` |
| 26 | `'--wheelhouse'` | `type=Path; required=True` |
| 27 | `'--suffix'` | `default='.whl'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `verify_wheelhouse` / 16 | `set(actual) != set(expected)` | `raise ValueError('wheelhouse file set does not match lock')` |
| `verify_wheelhouse` / 20 | `path.stat().st_size != metadata['bytes'] or sha256_file(path) != metadata['sha256']` | `raise ValueError(f'wheelhouse hash mismatch: {name}')` |

# cli：功能记录

上级模块：[模块说明](../modules/support-voice.md) · 实现：[voice_group/nlu_b2/cli.py](../../../voice_group/nlu_b2/cli.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [ASR、NLU、复核与命令交付](voice-command-production.md)

## 功能职责与范围

Command line entry for the B2 parser.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `main`

源码位置：[voice_group/nlu_b2/cli.py 第 14 行](../../../voice_group/nlu_b2/cli.py#L14)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_payload`

源码位置：[voice_group/nlu_b2/cli.py 第 30 行](../../../voice_group/nlu_b2/cli.py#L30)。类型：`FunctionDef`。

```python
_load_payload(args: argparse.Namespace) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `main` 调用：`CommandParser`, `CommandParser().parse`, `_load_payload`, `argparse.ArgumentParser`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`.
- `_load_payload` 调用：`Path`, `Path(args.input_file).read_text`, `SystemExit`, `json.loads`, `sys.stdin.read`, `sys.stdin.read().strip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_load_payload`，第 49 行：`SystemExit('请通过 --input、--intent/--text 或 stdin 提供输入')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 16 行：`parser.add_argument('--input', help='B1 result as a JSON string. If omitted, stdin is used.')`。
- 第 17 行：`parser.add_argument('--input-file', help='UTF-8 JSON file containing a B1 result.')`。
- 第 18 行：`parser.add_argument('--request-id', help='B1 request_id, used with --intent for quick tests.')`。
- 第 19 行：`parser.add_argument('--intent', help='Intent name, used with --text for quick tests.')`。
- 第 20 行：`parser.add_argument('--text', help='Normalized text, used with --intent for quick tests.')`。
- 第 21 行：`parser.add_argument('--intent-confidence', type=float, help='B1 intent confidence.')`。

## 上下游与关联验证

静态导入的项目内实现：

- [voice_group/nlu_b2/parser.py](../../../voice_group/nlu_b2/parser.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-voice.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `voice_group/nlu_b2/cli.py`

来源 SHA256：`f9060dd000487db4e8510cb33f9273aeab7fb955db9cd89cfeac87e87310e23e`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 16 | `'--input'` | `help='B1 result as a JSON string. If omitted, stdin is used.'` |
| 17 | `'--input-file'` | `help='UTF-8 JSON file containing a B1 result.'` |
| 18 | `'--request-id'` | `help='B1 request_id, used with --intent for quick tests.'` |
| 19 | `'--intent'` | `help='Intent name, used with --text for quick tests.'` |
| 20 | `'--text'` | `help='Normalized text, used with --intent for quick tests.'` |
| 21 | `'--intent-confidence'` | `type=float; help='B1 intent confidence.'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_load_payload` / 49 | `not raw` | `raise SystemExit('请通过 --input、--intent/--text 或 stdin 提供输入')` |

# create_qwen_launch_logs：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/create_qwen_launch_logs.py](../../../tools/create_qwen_launch_logs.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Allocate fresh, private Qwen launch logs without reusing prior evidence.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `create_launch_logs`

源码位置：[tools/create_qwen_launch_logs.py 第 10 行](../../../tools/create_qwen_launch_logs.py#L10)。类型：`FunctionDef`。

```python
create_launch_logs(output_root: Path, launch_id: UUID | None=None) -> str
```

Create this launch's raw/evidence/runtime files exclusively and return its UUID.

### `main`

源码位置：[tools/create_qwen_launch_logs.py 第 32 行](../../../tools/create_qwen_launch_logs.py#L32)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `create_launch_logs` 调用：`ValueError`, `created.append`, `os.close`, `os.open`, `output_root.mkdir`, `path.unlink`, `str`, `uuid4`.
- `main` 调用：`argparse.ArgumentParser`, `create_launch_logs`, `parser.add_argument`, `parser.parse_args`, `print`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `create_launch_logs`，第 28 行：`ValueError(f'Qwen launch log collision: {exc.filename}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 34 行：`parser.add_argument('--output-root', type=Path, required=True)`。

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

### `tools/create_qwen_launch_logs.py`

来源 SHA256：`d10e2ecfc03690620a9d36798143df5a1f6afae7e45f42897c5cccb54e02b7fb`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 34 | `'--output-root'` | `type=Path; required=True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `create_launch_logs` / 28 | `except FileExistsError` | `raise ValueError(f'Qwen launch log collision: {exc.filename}') from exc` |

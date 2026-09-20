# run_qwen_vl_decision：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_qwen_vl_decision.py](../../../tools/run_qwen_vl_decision.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run one strict high-level decision with a local Qwen2.5-VL checkpoint.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `load_context`

源码位置：[tools/run_qwen_vl_decision.py 第 13 行](../../../tools/run_qwen_vl_decision.py#L13)。类型：`FunctionDef`。

```python
load_context(path: Path) -> QwenInputContext
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_mapping`

源码位置：[tools/run_qwen_vl_decision.py 第 29 行](../../../tools/run_qwen_vl_decision.py#L29)。类型：`FunctionDef`。

```python
_mapping(payload: Mapping[str, Any], name: str) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_qwen_vl_decision.py 第 36 行](../../../tools/run_qwen_vl_decision.py#L36)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `load_context` 调用：`QwenInputContext`, `TypeError`, `_mapping`, `isinstance`, `json.loads`, `path.read_text`, `payload.get`.
- `_mapping` 调用：`TypeError`, `isinstance`, `payload.get`.
- `main` 调用：`StrictQwenVLAdapter.from_local_checkpoint`, `adapter`, `argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `json.dumps`, `load_context`, `parser.add_argument`, `parser.parse_args`, `print`, `str`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_mapping`，第 32 行：`TypeError(f'{name} must be an object')`。
- `load_context`，第 16 行：`TypeError('context file must contain one JSON object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 38 行：`parser.add_argument('context_json', type=Path)`。
- 第 39 行：`parser.add_argument('--model-path', required=True, type=Path)`。
- 第 40 行：`parser.add_argument('--image-root', type=Path)`。
- 第 41 行：`parser.add_argument('--max-new-tokens', type=int, default=48)`。
- 第 42 行：`parser.add_argument('--awq-backend', choices=('auto', 'torch_awq', 'gemm', 'gemm_triton'), default='auto')`。
- 第 47 行：`parser.add_argument('--output', required=True, type=Path)`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_vl_cli.py](../../../integration/tests/test_qwen_vl_cli.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_qwen_vl_decision.py`

来源 SHA256：`d8597a5e68248ee2ec635b8e0aa73650e5b7235942550b97b191cc9c8493a9fc`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 38 | `'context_json'` | `type=Path` |
| 39 | `'--model-path'` | `required=True; type=Path` |
| 40 | `'--image-root'` | `type=Path` |
| 41 | `'--max-new-tokens'` | `type=int; default=48` |
| 42 | `'--awq-backend'` | `choices=('auto', 'torch_awq', 'gemm', 'gemm_triton'); default='auto'` |
| 47 | `'--output'` | `required=True; type=Path` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `load_context` / 16 | `not isinstance(payload, Mapping)` | `raise TypeError('context file must contain one JSON object')` |
| `_mapping` / 32 | `not isinstance(value, Mapping)` | `raise TypeError(f'{name} must be an object')` |

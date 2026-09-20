# verify_qwen_kernel：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/verify_qwen_kernel.py](../../../tools/verify_qwen_kernel.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Strict parser for one Qwen GPTQ/Marlin launch evidence block.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_complete_blocks`

源码位置：[tools/verify_qwen_kernel.py 第 33 行](../../../tools/verify_qwen_kernel.py#L33)。类型：`FunctionDef`。

```python
_complete_blocks(lines: list[str]) -> list[list[str]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_kernel_log`

源码位置：[tools/verify_qwen_kernel.py 第 64 行](../../../tools/verify_qwen_kernel.py#L64)。类型：`FunctionDef`。

```python
verify_kernel_log(path: Path) -> dict[str, str]
```

Return runtime evidence only for the unique complete ready launch block.

## 内部调用与异常路径

- `_complete_blocks` 调用：`BEGIN_PATTERN.fullmatch`, `END_PATTERN.fullmatch`, `ValueError`, `active_lines.append`, `blocks.append`, `line.startswith`.
- `verify_kernel_log` 调用：`GEMV_PATTERN.fullmatch`, `MARLIN_PATTERN.fullmatch`, `QUANTIZATION_PATTERN.fullmatch`, `ValueError`, `_complete_blocks`, `any`, `len`, `path.read_text`, `path.read_text(encoding='utf-8', errors='replace').splitlines`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_complete_blocks`，第 41 行：`ValueError('invalid Qwen launch BEGIN evidence marker')`。
- `_complete_blocks`，第 43 行：`ValueError('nested Qwen launch evidence blocks are not allowed')`。
- `_complete_blocks`，第 50 行：`ValueError('invalid Qwen launch END evidence marker')`。
- `_complete_blocks`，第 52 行：`ValueError('Qwen launch END launch_id does not match BEGIN')`。
- `_complete_blocks`，第 60 行：`ValueError('unterminated Qwen launch evidence block')`。
- `verify_kernel_log`，第 74 行：`ValueError('no complete Qwen launch block proves auto_gptq and Marlin')`。
- `verify_kernel_log`，第 76 行：`ValueError('expected exactly one complete ready Qwen launch block')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_vllm_cu132_build.py](../../../integration/tests/test_vllm_cu132_build.py)
- [tools/repro_cli.py](../../../tools/repro_cli.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/verify_qwen_kernel.py`

来源 SHA256：`e5b74bab0873e4470bd2138fe6ae1b767cb454afd8dda8f2b4275260cc41cad2`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_complete_blocks` / 41 | `line.startswith(LAUNCH_BEGIN) AND match is None` | `raise ValueError('invalid Qwen launch BEGIN evidence marker')` |
| `_complete_blocks` / 43 | `line.startswith(LAUNCH_BEGIN) AND active_id is not None` | `raise ValueError('nested Qwen launch evidence blocks are not allowed')` |
| `_complete_blocks` / 50 | `line.startswith(LAUNCH_END) AND match is None or active_id is None` | `raise ValueError('invalid Qwen launch END evidence marker')` |
| `_complete_blocks` / 52 | `line.startswith(LAUNCH_END) AND match['launch_id'] != active_id` | `raise ValueError('Qwen launch END launch_id does not match BEGIN')` |
| `_complete_blocks` / 60 | `active_id is not None` | `raise ValueError('unterminated Qwen launch evidence block')` |
| `verify_kernel_log` / 74 | `not ready` | `raise ValueError('no complete Qwen launch block proves auto_gptq and Marlin')` |
| `verify_kernel_log` / 76 | `len(ready) != 1` | `raise ValueError('expected exactly one complete ready Qwen launch block')` |

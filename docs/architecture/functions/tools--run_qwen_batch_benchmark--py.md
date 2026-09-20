# run_qwen_batch_benchmark：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_qwen_batch_benchmark.py](../../../tools/run_qwen_batch_benchmark.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run a frozen proxy set through one loaded local Qwen2.5-VL checkpoint.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_percentile`

源码位置：[tools/run_qwen_batch_benchmark.py 第 15 行](../../../tools/run_qwen_batch_benchmark.py#L15)。类型：`FunctionDef`。

```python
_percentile(values: list[float], quantile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_cases`

源码位置：[tools/run_qwen_batch_benchmark.py 第 26 行](../../../tools/run_qwen_batch_benchmark.py#L26)。类型：`FunctionDef`。

```python
_load_cases(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_context`

源码位置：[tools/run_qwen_batch_benchmark.py 第 37 行](../../../tools/run_qwen_batch_benchmark.py#L37)。类型：`FunctionDef`。

```python
_context(case: dict[str, Any], fallback_image_name: str | None, index: int) -> QwenInputContext
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_evaluate`

源码位置：[tools/run_qwen_batch_benchmark.py 第 74 行](../../../tools/run_qwen_batch_benchmark.py#L74)。类型：`FunctionDef`。

```python
_evaluate(case: dict[str, Any], decision: dict[str, Any]) -> dict[str, bool]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_qwen_batch_benchmark.py 第 109 行](../../../tools/run_qwen_batch_benchmark.py#L109)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_percentile` 调用：`int`, `len`, `min`, `sorted`.
- `_load_cases` 调用：`ValueError`, `any`, `isinstance`, `json.loads`, `line.strip`, `path.read_text`, `path.read_text(encoding='utf-8').splitlines`.
- `_context` 调用：`QwenInputContext`, `ValueError`, `case.get`, `str`.
- `_evaluate` 调用：`abs`, `decision.get`, `expected.get`, `float`.
- `main` 调用：`(image_root / image_ref).resolve`, `FileNotFoundError`, `StrictQwenVLAdapter.from_local_checkpoint`, `ValueError`, `_context`, `_evaluate`, `_load_cases`, `_percentile`, `adapter`, `argparse.ArgumentParser`, `args.image.resolve`, `args.image_root.resolve`, `args.model_path.resolve`, `args.output.parent.mkdir`, `args.output.write_text`, `case.get`, `count`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `enumerate`, `float`, `image_group.add_argument`, `json.dumps`, `len`, `max`, `parser.add_argument`, `parser.add_mutually_exclusive_group`, `parser.parse_args`, `print`, `records.append`, `resolved.is_file`, `set`, `sorted`, `statistics.fmean`, `str`, `sum`, `type`, `zip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_context`，第 44 行：`ValueError(f"case {case.get('case_id', index)!r} has no rgb_ref")`。
- `_load_cases`，第 33 行：`ValueError('case file must contain JSON objects')`。
- `main`，第 144 行：`ValueError(f'rgb_ref escapes image root: {image_ref!r}')`。
- `main`，第 146 行：`FileNotFoundError(f'rgb_ref not found: {resolved}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 111 行：`parser.add_argument('cases', type=Path)`。
- 第 112 行：`parser.add_argument('--model-path', required=True, type=Path)`。
- 第 114 行：`image_group.add_argument('--image', type=Path, help='fallback image used by cases without rgb_ref')`。
- 第 119 行：`image_group.add_argument('--image-root', type=Path, help="root for each case's relative rgb_ref")`。
- 第 124 行：`parser.add_argument('--output', required=True, type=Path)`。
- 第 125 行：`parser.add_argument('--max-new-tokens', type=int, default=48)`。
- 第 126 行：`parser.add_argument('--awq-backend', choices=('auto', 'torch_awq', 'gemm', 'gemm_triton'), default='auto')`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_batch_benchmark.py](../../../integration/tests/test_qwen_batch_benchmark.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_qwen_batch_benchmark.py`

来源 SHA256：`c25537a9f480a8abd0518f2613e8ca319a175831476bb00eb3819bdd00dee8a7`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 111 | `'cases'` | `type=Path` |
| 112 | `'--model-path'` | `required=True; type=Path` |
| 114 | `'--image'` | `type=Path; help='fallback image used by cases without rgb_ref'` |
| 119 | `'--image-root'` | `type=Path; help="root for each case's relative rgb_ref"` |
| 124 | `'--output'` | `required=True; type=Path` |
| 125 | `'--max-new-tokens'` | `type=int; default=48` |
| 126 | `'--awq-backend'` | `choices=('auto', 'torch_awq', 'gemm', 'gemm_triton'); default='auto'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_load_cases` / 33 | `not cases or any((not isinstance(case, dict) for case in cases))` | `raise ValueError('case file must contain JSON objects')` |
| `_context` / 44 | `not image_name` | `raise ValueError(f"case {case.get('case_id', index)!r} has no rgb_ref")` |
| `main` / 144 | `image_root not in resolved.parents and resolved != image_root` | `raise ValueError(f'rgb_ref escapes image root: {image_ref!r}')` |
| `main` / 146 | `not resolved.is_file()` | `raise FileNotFoundError(f'rgb_ref not found: {resolved}')` |

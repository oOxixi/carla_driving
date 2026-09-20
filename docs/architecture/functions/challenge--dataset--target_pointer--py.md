# target_pointer：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/target_pointer.py](../../../challenge/dataset/target_pointer.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

target_pointer

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `read_jsonl`

源码位置：[challenge/dataset/target_pointer.py 第 11 行](../../../challenge/dataset/target_pointer.py#L11)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_jsonl`

源码位置：[challenge/dataset/target_pointer.py 第 36 行](../../../challenge/dataset/target_pointer.py#L36)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_target_index`

源码位置：[challenge/dataset/target_pointer.py 第 60 行](../../../challenge/dataset/target_pointer.py#L60)。类型：`FunctionDef`。

```python
build_target_index(targets: Any, top_k: int) -> tuple[list[dict[str, Any]], dict[str, int]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `encode_step`

源码位置：[challenge/dataset/target_pointer.py 第 84 行](../../../challenge/dataset/target_pointer.py#L84)。类型：`FunctionDef`。

```python
encode_step(step: dict[str, Any], target_map: dict[str, int], no_target_index: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `process_sample`

源码位置：[challenge/dataset/target_pointer.py 第 132 行](../../../challenge/dataset/target_pointer.py#L132)。类型：`FunctionDef`。

```python
process_sample(sample: dict[str, Any], top_k: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/target_pointer.py 第 201 行](../../../challenge/dataset/target_pointer.py#L201)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `read_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.open`, `rows.append`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `build_target_index` 调用：`enumerate`, `isinstance`, `selected.append`, `target.get`.
- `encode_step` 调用：`isinstance`, `step.get`, `target.get`.
- `process_sample` 调用：`build_target_index`, `encode_step`, `encoded_steps.append`, `isinstance`, `item.get`, `model_request.get`, `sample.get`, `teacher_plan.get`.
- `main` 调用：`Path`, `SystemExit`, `argparse.ArgumentParser`, `len`, `output.append`, `parser.add_argument`, `parser.parse_args`, `print`, `process_sample`, `read_jsonl`, `sample.get`, `sample.get('student_targets', {}).get`, `step.get`, `write_jsonl`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 223 行：`SystemExit('--top-k must be > 0')`。
- `main`，第 286 行：`SystemExit(2)`。
- `read_jsonl`，第 22 行：`ValueError(f'{path}:{line_no}: invalid JSON: {exc}')`。
- `read_jsonl`，第 27 行：`ValueError(f'{path}:{line_no}: row is not object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 204 行：`parser.add_argument('--input', required=True)`。
- 第 209 行：`parser.add_argument('--output', required=True)`。
- 第 214 行：`parser.add_argument('--top-k', type=int, default=8)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/target_pointer.py`

来源 SHA256：`57748670c14d0f0f9010ee2181e219f4102382a42aa567d2954b834322aaa000`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 204 | `'--input'` | `required=True` |
| 209 | `'--output'` | `required=True` |
| 214 | `'--top-k'` | `type=int; default=8` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 22 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc` |
| `read_jsonl` / 27 | `not isinstance(row, dict)` | `raise ValueError(f'{path}:{line_no}: row is not object')` |
| `main` / 223 | `args.top_k <= 0` | `raise SystemExit('--top-k must be > 0')` |
| `main` / 286 | `outside_topk > 0` | `raise SystemExit(2)` |

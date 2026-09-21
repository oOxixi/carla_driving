# validate_dataset：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/validate_dataset.py](../../../challenge/dataset/validate_dataset.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

validate_dataset

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `read_jsonl`

源码位置：[challenge/dataset/validate_dataset.py 第 12 行](../../../challenge/dataset/validate_dataset.py#L12)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_sample`

源码位置：[challenge/dataset/validate_dataset.py 第 37 行](../../../challenge/dataset/validate_dataset.py#L37)。类型：`FunctionDef`。

```python
validate_sample(sample: dict[str, Any]) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/validate_dataset.py 第 106 行](../../../challenge/dataset/validate_dataset.py#L106)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `read_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.open`, `rows.append`.
- `validate_sample` 调用：`errors.append`, `grounding.get`, `isinstance`, `len`, `model_request.get`, `quality.get`, `sample.get`, `teacher_plan.get`, `visual.get`.
- `main` 调用：`Counter`, `Path`, `SystemExit`, `all_errors.append`, `argparse.ArgumentParser`, `classes.items`, `duplicate_ids.append`, `enumerate`, `isinstance`, `json.dumps`, `len`, `metadata.get`, `model_ids.items`, `parser.add_argument`, `parser.parse_args`, `print`, `read_jsonl`, `sample.get`, `sample_class.get`, `scenarios.items`, `seen_ids.add`, `set`, `str`, `validate_sample`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 171 行：`SystemExit(1)`。
- `main`，第 178 行：`SystemExit(1)`。
- `read_jsonl`，第 23 行：`ValueError(f'{path}:{line_no}: invalid JSON: {exc}')`。
- `read_jsonl`，第 28 行：`ValueError(f'{path}:{line_no}: non-object row')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 108 行：`parser.add_argument('dataset')`。

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

### `challenge/dataset/validate_dataset.py`

来源 SHA256：`a976b358c3ce18bd3d80747bcb4eb2d17e38a6bd673f9a2df2385135fda12ecf`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 108 | `'dataset'` | `` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 23 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc` |
| `read_jsonl` / 28 | `not isinstance(obj, dict)` | `raise ValueError(f'{path}:{line_no}: non-object row')` |
| `main` / 171 | `all_errors` | `raise SystemExit(1)` |
| `main` / 178 | `duplicate_ids` | `raise SystemExit(1)` |

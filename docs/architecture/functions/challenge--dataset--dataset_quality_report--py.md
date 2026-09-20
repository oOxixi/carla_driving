# dataset_quality_report：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/dataset_quality_report.py](../../../challenge/dataset/dataset_quality_report.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

dataset_quality_report

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `read_jsonl`

源码位置：[challenge/dataset/dataset_quality_report.py 第 14 行](../../../challenge/dataset/dataset_quality_report.py#L14)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_json`

源码位置：[challenge/dataset/dataset_quality_report.py 第 42 行](../../../challenge/dataset/dataset_quality_report.py#L42)。类型：`FunctionDef`。

```python
read_json(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sha256_file`

源码位置：[challenge/dataset/dataset_quality_report.py 第 58 行](../../../challenge/dataset/dataset_quality_report.py#L58)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `get_dict`

源码位置：[challenge/dataset/dataset_quality_report.py 第 71 行](../../../challenge/dataset/dataset_quality_report.py#L71)。类型：`FunctionDef`。

```python
get_dict(sample: dict[str, Any], key: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sample_class`

源码位置：[challenge/dataset/dataset_quality_report.py 第 83 行](../../../challenge/dataset/dataset_quality_report.py#L83)。类型：`FunctionDef`。

```python
sample_class(sample: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `rejection_counts`

源码位置：[challenge/dataset/dataset_quality_report.py 第 99 行](../../../challenge/dataset/dataset_quality_report.py#L99)。类型：`FunctionDef`。

```python
rejection_counts(rows: list[dict[str, Any]]) -> Counter
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `append_counter`

源码位置：[challenge/dataset/dataset_quality_report.py 第 133 行](../../../challenge/dataset/dataset_quality_report.py#L133)。类型：`FunctionDef`。

```python
append_counter(lines: list[str], counter: Counter) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/dataset_quality_report.py 第 149 行](../../../challenge/dataset/dataset_quality_report.py#L149)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `read_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.is_file`, `path.open`, `rows.append`.
- `read_json` 调用：`FileNotFoundError`, `ValueError`, `isinstance`, `json.loads`, `path.is_file`, `path.read_text`.
- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `get_dict` 调用：`isinstance`, `sample.get`.
- `sample_class` 调用：`get_dict`, `obj.get`, `str`.
- `rejection_counts` 调用：`Counter`, `get_dict`, `isinstance`, `quality.get`, `row.get`, `str`.
- `append_counter` 调用：`counter.items`, `lines.append`, `sorted`.
- `main` 调用：`'\n'.join`, `Counter`, `Path`, `SystemExit`, `append_counter`, `argparse.ArgumentParser`, `counts.get`, `dataset_manifest.get`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `get_dict`, `get_dict(x, 'metadata').get`, `isinstance`, `len`, `lines.append`, `metadata.get`, `model_request.get`, `output_path.parent.mkdir`, `output_path.write_text`, `parser.add_argument`, `parser.parse_args`, `path.is_file`, `policy.get`, `print`, `quality.get`, `read_json`, `read_jsonl`, `rejection_counts`, `sample.get`, `sample_class`, `sha256_file`, `split_manifest.get`, `step.get`, `str`, `student_targets.get`, `teacher_plan.get`, `train_classes.get`, `val_classes.get`, `visual.get`, `x.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 294 行：`SystemExit('raw-valid and with-targets counts differ')`。
- `main`，第 299 行：`SystemExit('raw-valid and with-policy counts differ')`。
- `main`，第 308 行：`SystemExit('training policy partition does not cover raw dataset')`。
- `main`，第 317 行：`SystemExit('Train + Val does not equal train-eligible dataset')`。
- `read_json`，第 44 行：`FileNotFoundError(path)`。
- `read_json`，第 51 行：`ValueError(f'{path}: expected JSON object')`。
- `read_jsonl`，第 28 行：`ValueError(f'{path}:{line_no}: invalid JSON: {exc}')`。
- `read_jsonl`，第 33 行：`ValueError(f'{path}:{line_no}: row is not a JSON object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 152 行：`parser.add_argument('--raw-valid', required=True)`。
- 第 157 行：`parser.add_argument('--with-targets', required=True)`。
- 第 162 行：`parser.add_argument('--with-policy', required=True)`。
- 第 167 行：`parser.add_argument('--train-eligible', required=True)`。
- 第 172 行：`parser.add_argument('--hard-cases', required=True)`。
- 第 177 行：`parser.add_argument('--rejected', required=True)`。
- 第 182 行：`parser.add_argument('--train', required=True)`。
- 第 187 行：`parser.add_argument('--val', required=True)`。
- 第 192 行：`parser.add_argument('--dataset-manifest', required=True)`。
- 第 197 行：`parser.add_argument('--split-manifest', required=True)`。
- 第 202 行：`parser.add_argument('--output', required=True)`。

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

### `challenge/dataset/dataset_quality_report.py`

来源 SHA256：`a7751982c65d631eacbd8c7f854997e76e7d67c034af504d13718cb7b6e9a3ba`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 152 | `'--raw-valid'` | `required=True` |
| 157 | `'--with-targets'` | `required=True` |
| 162 | `'--with-policy'` | `required=True` |
| 167 | `'--train-eligible'` | `required=True` |
| 172 | `'--hard-cases'` | `required=True` |
| 177 | `'--rejected'` | `required=True` |
| 182 | `'--train'` | `required=True` |
| 187 | `'--val'` | `required=True` |
| 192 | `'--dataset-manifest'` | `required=True` |
| 197 | `'--split-manifest'` | `required=True` |
| 202 | `'--output'` | `required=True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 28 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc` |
| `read_jsonl` / 33 | `not isinstance(row, dict)` | `raise ValueError(f'{path}:{line_no}: row is not a JSON object')` |
| `read_json` / 44 | `not path.is_file()` | `raise FileNotFoundError(path)` |
| `read_json` / 51 | `not isinstance(value, dict)` | `raise ValueError(f'{path}: expected JSON object')` |
| `main` / 294 | `len(raw_valid) != len(with_targets)` | `raise SystemExit('raw-valid and with-targets counts differ')` |
| `main` / 299 | `len(raw_valid) != len(with_policy)` | `raise SystemExit('raw-valid and with-policy counts differ')` |
| `main` / 308 | `len(train_eligible) + len(hard_cases) != len(raw_valid)` | `raise SystemExit('training policy partition does not cover raw dataset')` |
| `main` / 317 | `len(train) + len(val) != len(train_eligible)` | `raise SystemExit('Train + Val does not equal train-eligible dataset')` |

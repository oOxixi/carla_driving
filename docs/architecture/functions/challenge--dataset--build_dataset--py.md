# build_dataset：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_dataset.py](../../../challenge/dataset/build_dataset.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_dataset

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_dataset.py 第 20 行](../../../challenge/dataset/build_dataset.py#L20)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `read_jsonl`

源码位置：[challenge/dataset/build_dataset.py 第 28 行](../../../challenge/dataset/build_dataset.py#L28)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

`read_jsonl` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `write_jsonl`

源码位置：[challenge/dataset/build_dataset.py 第 44 行](../../../challenge/dataset/build_dataset.py#L44)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

`write_jsonl` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `normalize_class`

源码位置：[challenge/dataset/build_dataset.py 第 59 行](../../../challenge/dataset/build_dataset.py#L59)。类型：`FunctionDef`。

```python
normalize_class(sample: dict[str, Any]) -> str
```

`normalize_class` 从显式输入构造版本化样本、计划、清单或派生视图；保持原始记录不变，并把默认、排除原因与来源身份写入新产物。

### `packaged_rgb_path`

源码位置：[challenge/dataset/build_dataset.py 第 69 行](../../../challenge/dataset/build_dataset.py#L69)。类型：`FunctionDef`。

```python
packaged_rgb_path(sample: dict[str, Any], *, package_root: Path | None, output_dir: Path) -> tuple[str, str | None]
```

`packaged_rgb_path` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `build_training_record`

源码位置：[challenge/dataset/build_dataset.py 第 110 行](../../../challenge/dataset/build_dataset.py#L110)。类型：`FunctionDef`。

```python
build_training_record(sample: dict[str, Any], *, split: str, dataset_version: str, package_root: Path | None, output_dir: Path) -> dict[str, Any]
```

`build_training_record` 从显式输入构造版本化样本、计划、清单或派生视图；保持原始记录不变，并把默认、排除原因与来源身份写入新产物。

### `main`

源码位置：[challenge/dataset/build_dataset.py 第 194 行](../../../challenge/dataset/build_dataset.py#L194)。类型：`FunctionDef`。

```python
main() -> None
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `read_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.open`, `rows.append`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `normalize_class` 调用：`ValueError`, `isinstance`, `sample.get`, `sample_class.get`, `str`, `str(sample_class.get('primary', '')).upper`.
- `packaged_rgb_path` 调用：`(package_root / 'rgb').glob`, `Path`, `Path(__import__('os').path.relpath(rgb_file, start=output_dir.resolve())).as_posix`, `ValueError`, `__import__`, `__import__('os').path.relpath`, `candidates[0].resolve`, `isinstance`, `len`, `list`, `output_dir.resolve`, `rgb_file.as_posix`, `sample.get`, `sha256_file`, `visual.get`.
- `build_training_record` 调用：`(sample.get('visual_input') or {}).get`, `ValueError`, `bool`, `copy.deepcopy`, `isinstance`, `model_request.get`, `normalize_class`, `packaged_rgb_path`, `quality.get`, `sample.get`, `teacher_plan.get`, `training_policy.get`.
- `main` 调用：`(output_dir / 'a3_view_manifest.json').write_text`, `Counter`, `Path`, `Path(args.package_root).resolve`, `RuntimeError`, `argparse.ArgumentParser`, `build_training_record`, `class_counts['train'].items`, `class_counts['val'].items`, `converted_train.append`, `converted_val.append`, `dict`, `json.dumps`, `len`, `output_dir.mkdir`, `parser.add_argument`, `parser.parse_args`, `print`, `read_jsonl`, `sha256_file`, `sorted`, `str`, `write_jsonl`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `build_training_record`，第 119 行：`ValueError(f'unsupported split: {split}')`。
- `build_training_record`，第 128 行：`ValueError('model_request missing')`。
- `build_training_record`，第 130 行：`ValueError('teacher_plan missing')`。
- `build_training_record`，第 132 行：`ValueError('metadata missing')`。
- `build_training_record`，第 134 行：`ValueError('quality missing')`。
- `build_training_record`，第 136 行：`ValueError('training_policy missing')`。
- `build_training_record`，第 138 行：`ValueError('non-train-eligible sample must not enter Train/Val view')`。
- `build_training_record`，第 141 行：`ValueError('request_id mismatch')`。
- `build_training_record`，第 143 行：`ValueError('command_id mismatch')`。
- `main`，第 248 行：`RuntimeError('sample ID leakage detected')`。
- `normalize_class`，第 62 行：`ValueError('sample_class must be object')`。
- `normalize_class`，第 65 行：`ValueError(f'unsupported sample class: {primary!r}')`。
- `packaged_rgb_path`，第 77 行：`ValueError('visual_input missing')`。
- `packaged_rgb_path`，第 81 行：`ValueError('visual_input.rgb_sha256 missing or invalid')`。
- `packaged_rgb_path`，第 87 行：`ValueError('visual_input.rgb_ref missing')`。
- `packaged_rgb_path`，第 92 行：`ValueError(f'expected exactly one packaged RGB for {digest}, found {len(candidates)}')`。
- `packaged_rgb_path`，第 98 行：`ValueError(f'packaged RGB SHA mismatch: {rgb_file}')`。
- `read_jsonl`，第 37 行：`ValueError(f'{path}:{line_no}: invalid JSON: {exc}')`。
- `read_jsonl`，第 39 行：`ValueError(f'{path}:{line_no}: record must be object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 196 行：`parser.add_argument('--train', required=True)`。
- 第 197 行：`parser.add_argument('--val', required=True)`。
- 第 198 行：`parser.add_argument('--output-dir', required=True)`。
- 第 199 行：`parser.add_argument('--dataset-version', required=True)`。
- 第 200 行：`parser.add_argument('--package-root', help='Optional delivery package root containing rgb/<sha256>.*. When supplied, input.rgb_ref is rewritten to a portable path relative to the output JSONL directory.')`。

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

### `challenge/dataset/build_dataset.py`

来源 SHA256：`80a848bbbaeb17e43a34102998b1268b1dab9537cb97fda2df481958bff66249`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 196 | `'--train'` | `required=True` |
| 197 | `'--val'` | `required=True` |
| 198 | `'--output-dir'` | `required=True` |
| 199 | `'--dataset-version'` | `required=True` |
| 200 | `'--package-root'` | `help='Optional delivery package root containing rgb/<sha256>.*. When supplied, input.rgb_ref is rewritten to a portable path relative to the output JSONL directory.'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 37 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc` |
| `read_jsonl` / 39 | `not isinstance(row, dict)` | `raise ValueError(f'{path}:{line_no}: record must be object')` |
| `normalize_class` / 62 | `not isinstance(sample_class, dict)` | `raise ValueError('sample_class must be object')` |
| `normalize_class` / 65 | `primary not in VALID_CLASSES` | `raise ValueError(f'unsupported sample class: {primary!r}')` |
| `packaged_rgb_path` / 77 | `not isinstance(visual, dict)` | `raise ValueError('visual_input missing')` |
| `packaged_rgb_path` / 81 | `not isinstance(digest, str) or len(digest) != 64` | `raise ValueError('visual_input.rgb_sha256 missing or invalid')` |
| `packaged_rgb_path` / 87 | `package_root is None AND not isinstance(rgb_ref, str) or not rgb_ref` | `raise ValueError('visual_input.rgb_ref missing')` |
| `packaged_rgb_path` / 92 | `len(candidates) != 1` | `raise ValueError(f'expected exactly one packaged RGB for {digest}, found {len(candidates)}')` |
| `packaged_rgb_path` / 98 | `sha256_file(rgb_file) != digest` | `raise ValueError(f'packaged RGB SHA mismatch: {rgb_file}')` |
| `build_training_record` / 119 | `split not in {'train', 'val'}` | `raise ValueError(f'unsupported split: {split}')` |
| `build_training_record` / 128 | `not isinstance(model_request, dict)` | `raise ValueError('model_request missing')` |
| `build_training_record` / 130 | `not isinstance(teacher_plan, dict)` | `raise ValueError('teacher_plan missing')` |
| `build_training_record` / 132 | `not isinstance(metadata, dict)` | `raise ValueError('metadata missing')` |
| `build_training_record` / 134 | `not isinstance(quality, dict)` | `raise ValueError('quality missing')` |
| `build_training_record` / 136 | `not isinstance(training_policy, dict)` | `raise ValueError('training_policy missing')` |
| `build_training_record` / 138 | `training_policy.get('train_eligible') is not True` | `raise ValueError('non-train-eligible sample must not enter Train/Val view')` |
| `build_training_record` / 141 | `teacher_plan.get('request_id') != model_request.get('request_id')` | `raise ValueError('request_id mismatch')` |
| `build_training_record` / 143 | `teacher_plan.get('command_id') != model_request.get('command_id')` | `raise ValueError('command_id mismatch')` |
| `main` / 248 | `overlap` | `raise RuntimeError('sample ID leakage detected')` |

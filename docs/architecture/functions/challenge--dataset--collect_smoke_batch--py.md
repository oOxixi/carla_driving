# collect_smoke_batch：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/collect_smoke_batch.py](../../../challenge/dataset/collect_smoke_batch.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

collect_smoke_batch

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `load_json`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 82 行](../../../challenge/dataset/collect_smoke_batch.py#L82)。类型：`FunctionDef`。

```python
load_json(path: Path) -> dict[str, Any] | None
```

`load_json` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `count_jsonl_rows`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 91 行](../../../challenge/dataset/collect_smoke_batch.py#L91)。类型：`FunctionDef`。

```python
count_jsonl_rows(path: Path) -> int
```

`count_jsonl_rows` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `read_jsonl`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 99 行](../../../challenge/dataset/collect_smoke_batch.py#L99)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

`read_jsonl` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `validate_teacher`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 118 行](../../../challenge/dataset/collect_smoke_batch.py#L118)。类型：`FunctionDef`。

```python
validate_teacher(service_url: str) -> None
```

`validate_teacher` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `collect_dataset`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 148 行](../../../challenge/dataset/collect_smoke_batch.py#L148)。类型：`FunctionDef`。

```python
collect_dataset(repo_root: Path, log_dir: Path, dataset_dir: Path) -> tuple[int, int]
```

`collect_dataset` 执行采集或从运行日志汇总样本/证据；运行成功、结构有效、闭环成功和训练资格是分开的判断，失败记录不得静默丢弃。

### `existing_valid_scenarios`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 202 行](../../../challenge/dataset/collect_smoke_batch.py#L202)。类型：`FunctionDef`。

```python
existing_valid_scenarios(dataset_dir: Path) -> set[str]
```

`existing_valid_scenarios` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `run_scenario`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 223 行](../../../challenge/dataset/collect_smoke_batch.py#L223)。类型：`FunctionDef`。

```python
run_scenario(repo_root: Path, scenario_path: str, service_url: str, log_dir: Path) -> int
```

`run_scenario` 执行采集或从运行日志汇总样本/证据；运行成功、结构有效、闭环成功和训练资格是分开的判断，失败记录不得静默丢弃。

### `validate_dataset`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 269 行](../../../challenge/dataset/collect_smoke_batch.py#L269)。类型：`FunctionDef`。

```python
validate_dataset(repo_root: Path, dataset_dir: Path) -> None
```

`validate_dataset` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `build_manifest`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 289 行](../../../challenge/dataset/collect_smoke_batch.py#L289)。类型：`FunctionDef`。

```python
build_manifest(repo_root: Path, dataset_dir: Path) -> None
```

`build_manifest` 从显式输入构造版本化样本、计划、清单或派生视图；保持原始记录不变，并把默认、排除原因与来源身份写入新产物。

### `main`

源码位置：[challenge/dataset/collect_smoke_batch.py 第 314 行](../../../challenge/dataset/collect_smoke_batch.py#L314)。类型：`FunctionDef`。

```python
main() -> None
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `load_json` 调用：`isinstance`, `json.loads`, `path.read_text`.
- `count_jsonl_rows` 调用：`line.strip`, `path.is_file`, `path.open`, `sum`.
- `read_jsonl` 调用：`isinstance`, `json.loads`, `line.strip`, `path.is_file`, `path.open`, `rows.append`.
- `validate_teacher` 调用：`RuntimeError`, `data.get`, `json.loads`, `print`, `response.read`, `service_url.rstrip`, `str`, `urllib.request.urlopen`.
- `collect_dataset` 调用：`RuntimeError`, `cmd.extend`, `count_jsonl_rows`, `log_dir.glob`, `sorted`, `str`, `subprocess.run`.
- `existing_valid_scenarios` 调用：`isinstance`, `metadata.get`, `read_jsonl`, `result.add`, `sample.get`, `set`.
- `run_scenario` 调用：`print`, `str`, `subprocess.run`.
- `validate_dataset` 调用：`RuntimeError`, `str`, `subprocess.run`.
- `build_manifest` 调用：`RuntimeError`, `str`, `subprocess.run`.
- `main` 调用：`Path`, `Path(__file__).resolve`, `RuntimeError`, `SystemExit`, `argparse.ArgumentParser`, `build_manifest`, `collect_dataset`, `data.get`, `dataset_dir.mkdir`, `enumerate`, `existing_valid_scenarios`, `failed_processes.append`, `image_dir.mkdir`, `isinstance`, `len`, `load_json`, `log_dir.mkdir`, `parser.add_argument`, `parser.parse_args`, `path.is_file`, `print`, `run_scenario`, `str`, `time.sleep`, `valid_scenarios.append`, `validate_dataset`, `validate_teacher`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `build_manifest`，第 311 行：`RuntimeError('build_manifest.py failed')`。
- `collect_dataset`，第 194 行：`RuntimeError('collector.py failed')`。
- `main`，第 336 行：`SystemExit('--target-valid must be between 20 and 50')`。
- `main`，第 390 行：`RuntimeError(f'Scenario not found: {relative_path}')`。
- `main`，第 397 行：`RuntimeError(f'Invalid scenario JSON: {relative_path}')`。
- `main`，第 573 行：`SystemExit(2)`。
- `validate_dataset`，第 286 行：`RuntimeError('validate_dataset.py failed')`。
- `validate_teacher`，第 130 行：`RuntimeError('Teacher service is not READY')`。
- `validate_teacher`，第 133 行：`RuntimeError('Teacher service is not production_ready')`。
- `validate_teacher`，第 136 行：`RuntimeError('Unexpected Teacher model: ' + str(data.get('model_id')))`。
- `validate_teacher`，第 142 行：`RuntimeError('Unexpected Teacher mode: ' + str(data.get('qwen_mode')))`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 317 行：`parser.add_argument('--target-valid', type=int, default=30)`。
- 第 323 行：`parser.add_argument('--qwen-service-url', default='http://127.0.0.1:18003')`。
- 第 328 行：`parser.add_argument('--dry-run', action='store_true')`。

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

### `challenge/dataset/collect_smoke_batch.py`

来源 SHA256：`f15040af6eae0062fb68a30e648a3d55e4ee32b9f4e7c8ccf5f75aacdc33026e`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 317 | `'--target-valid'` | `type=int; default=30` |
| 323 | `'--qwen-service-url'` | `default='http://127.0.0.1:18003'` |
| 328 | `'--dry-run'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `validate_teacher` / 130 | `data.get('status') != 'READY'` | `raise RuntimeError('Teacher service is not READY')` |
| `validate_teacher` / 133 | `data.get('production_ready') is not True` | `raise RuntimeError('Teacher service is not production_ready')` |
| `validate_teacher` / 136 | `data.get('model_id') != 'Qwen/Qwen3.5-2B'` | `raise RuntimeError('Unexpected Teacher model: ' + str(data.get('model_id')))` |
| `validate_teacher` / 142 | `data.get('qwen_mode') != 'planner_v2'` | `raise RuntimeError('Unexpected Teacher mode: ' + str(data.get('qwen_mode')))` |
| `collect_dataset` / 194 | `result.returncode != 0` | `raise RuntimeError('collector.py failed')` |
| `validate_dataset` / 286 | `result.returncode != 0` | `raise RuntimeError('validate_dataset.py failed')` |
| `build_manifest` / 311 | `result.returncode != 0` | `raise RuntimeError('build_manifest.py failed')` |
| `main` / 336 | `not 20 <= args.target_valid <= 50` | `raise SystemExit('--target-valid must be between 20 and 50')` |
| `main` / 390 | `not path.is_file()` | `raise RuntimeError(f'Scenario not found: {relative_path}')` |
| `main` / 397 | `data is None` | `raise RuntimeError(f'Invalid scenario JSON: {relative_path}')` |
| `main` / 573 | `NOT (accepted >= args.target_valid)` | `raise SystemExit(2)` |

# build_a3_d2_view：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_a3_d2_view.py](../../../challenge/dataset/build_a3_d2_view.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

Derive strict positive A3 supervision from B1's signed D2 v1.1 release.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_rows`

源码位置：[challenge/dataset/build_a3_d2_view.py 第 35 行](../../../challenge/dataset/build_a3_d2_view.py#L35)。类型：`FunctionDef`。

```python
_rows(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_jsonl`

源码位置：[challenge/dataset/build_a3_d2_view.py 第 40 行](../../../challenge/dataset/build_a3_d2_view.py#L40)。类型：`FunctionDef`。

```python
_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_cohort_identity`

源码位置：[challenge/dataset/build_a3_d2_view.py 第 46 行](../../../challenge/dataset/build_a3_d2_view.py#L46)。类型：`FunctionDef`。

```python
_cohort_identity(repo: Path, row: dict[str, Any]) -> dict[str, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_exclusion_reason`

源码位置：[challenge/dataset/build_a3_d2_view.py 第 82 行](../../../challenge/dataset/build_a3_d2_view.py#L82)。类型：`FunctionDef`。

```python
_exclusion_reason(row: dict[str, Any]) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_view`

源码位置：[challenge/dataset/build_a3_d2_view.py 第 99 行](../../../challenge/dataset/build_a3_d2_view.py#L99)。类型：`FunctionDef`。

```python
build_view(release_dir: Path, output_dir: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/build_a3_d2_view.py 第 162 行](../../../challenge/dataset/build_a3_d2_view.py#L162)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_rows` 调用：`json.loads`, `line.strip`, `path.open`.
- `_write_jsonl` 调用：`json.dumps`, `path.open`, `stream.write`.
- `_cohort_identity` 调用：`ValueError`, `canonical_text_sha256`, `json.loads`, `manifest.get`, `manifest_path.read_text`, `metadata.get`, `row.get`, `row['teacher_plan'].get`, `str`.
- `_exclusion_reason` 调用：`ValueError`, `loop.get`, `quality.get`, `row.get`.
- `build_view` 调用：`(output_dir / 'a3_view_manifest.json').write_text`, `Counter`, `ValueError`, `_cohort_identity`, `_exclusion_reason`, `_rows`, `_write_jsonl`, `canonical_text_sha256`, `cohort_counts.items`, `dict`, `excluded.append`, `json.dumps`, `kept[split].append`, `len`, `manifest_sources.items`, `output_dir.mkdir`, `path.stat`, `reason_counts.items`, `release_dir.resolve`, `sorted`, `str`, `validate_release`.
- `main` 调用：`Path`, `argparse.ArgumentParser`, `build_view`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_cohort_identity`，第 49 行：`ValueError(f'unsupported source cohort: {version}')`。
- `_cohort_identity`，第 53 行：`ValueError(f"{row['sample_id']}: collection Teacher SHA mismatch")`。
- `_cohort_identity`，第 61 行：`ValueError(f"{row['sample_id']}: baseline Teacher SHA mismatch")`。
- `_cohort_identity`，第 63 行：`ValueError(f"{row['sample_id']}: Teacher model ID mismatch")`。
- `_cohort_identity`，第 65 行：`ValueError(f"{row['sample_id']}: Teacher model revision mismatch")`。
- `_cohort_identity`，第 71 行：`ValueError(f"{row['sample_id']}: Teacher artifact fingerprint mismatch")`。
- `_exclusion_reason`，第 87 行：`ValueError(f"{row['sample_id']}: missing positive training eligibility")`。
- `build_view`，第 104 行：`ValueError('B1 signed release integrity gate must pass before A3 view generation')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 164 行：`parser.add_argument('--release-dir', type=Path, default=Path('challenge/dataset/releases/d2_v1_1'))`。
- 第 165 行：`parser.add_argument('--output-dir', type=Path, default=Path('artifacts/a3_d2_v1_1_positive_view_v1'))`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/dataset/validate_d2_release.py](../../../challenge/dataset/validate_d2_release.py)

静态 import 消费者（含测试）：

- [challenge/dataset/tests/test_build_a3_d2_view.py](../../../challenge/dataset/tests/test_build_a3_d2_view.py)
- [challenge/distillation/audit_d2_view.py](../../../challenge/distillation/audit_d2_view.py)
- [challenge/distillation/tests/test_audit_d2_view.py](../../../challenge/distillation/tests/test_audit_d2_view.py)
- [challenge/distillation/tests/test_d2_v1_1_smoke_gate.py](../../../challenge/distillation/tests/test_d2_v1_1_smoke_gate.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/build_a3_d2_view.py`

来源 SHA256：`63b24f449ba5ccf660210a3048d57d4a08185f33a3b2c48cb58e7120ea11d163`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 164 | `'--release-dir'` | `type=Path; default=Path('challenge/dataset/releases/d2_v1_1')` |
| 165 | `'--output-dir'` | `type=Path; default=Path('artifacts/a3_d2_v1_1_positive_view_v1')` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_cohort_identity` / 49 | `version not in COHORTS` | `raise ValueError(f'unsupported source cohort: {version}')` |
| `_cohort_identity` / 53 | `metadata.get('teacher_git_sha') != collection_sha` | `raise ValueError(f"{row['sample_id']}: collection Teacher SHA mismatch")` |
| `_cohort_identity` / 61 | `metadata.get('teacher_baseline_git_sha', baseline_sha) != baseline_sha` | `raise ValueError(f"{row['sample_id']}: baseline Teacher SHA mismatch")` |
| `_cohort_identity` / 63 | `(metadata.get('teacher_model_id') or row['teacher_plan'].get('model_id')) != model_id` | `raise ValueError(f"{row['sample_id']}: Teacher model ID mismatch")` |
| `_cohort_identity` / 65 | `metadata.get('teacher_model_revision', revision) != revision` | `raise ValueError(f"{row['sample_id']}: Teacher model revision mismatch")` |
| `_cohort_identity` / 71 | `recorded_fingerprint is not None and recorded_fingerprint != fingerprint` | `raise ValueError(f"{row['sample_id']}: Teacher artifact fingerprint mismatch")` |
| `_exclusion_reason` / 87 | `quality.get('valid_for_training') is not True` | `raise ValueError(f"{row['sample_id']}: missing positive training eligibility")` |
| `build_view` / 104 | `not release_check['valid'] or release_check['authoritative_manifest'] != 'release_manifest.json'` | `raise ValueError('B1 signed release integrity gate must pass before A3 view generation')` |

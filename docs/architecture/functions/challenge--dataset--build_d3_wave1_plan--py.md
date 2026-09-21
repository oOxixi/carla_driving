# build_d3_wave1_plan：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d3_wave1_plan.py](../../../challenge/dataset/build_d3_wave1_plan.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d3_wave1_plan

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 83 行](../../../challenge/dataset/build_d3_wave1_plan.py#L83)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `canonical_sha256`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 91 行](../../../challenge/dataset/build_d3_wave1_plan.py#L91)。类型：`FunctionDef`。

```python
canonical_sha256(obj: object) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_json`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 103 行](../../../challenge/dataset/build_d3_wave1_plan.py#L103)。类型：`FunctionDef`。

```python
load_json(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_jsonl`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 107 行](../../../challenge/dataset/build_d3_wave1_plan.py#L107)。类型：`FunctionDef`。

```python
load_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `row_family`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 118 行](../../../challenge/dataset/build_d3_wave1_plan.py#L118)。类型：`FunctionDef`。

```python
row_family(row: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `row_source`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 126 行](../../../challenge/dataset/build_d3_wave1_plan.py#L126)。类型：`FunctionDef`。

```python
row_source(row: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `plan_seed_values`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 130 行](../../../challenge/dataset/build_d3_wave1_plan.py#L130)。类型：`FunctionDef`。

```python
plan_seed_values(payload: dict[str, Any]) -> set[int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_teacher_manifest`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 147 行](../../../challenge/dataset/build_d3_wave1_plan.py#L147)。类型：`FunctionDef`。

```python
validate_teacher_manifest(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 180 行](../../../challenge/dataset/build_d3_wave1_plan.py#L180)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main.pool`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 408 行](../../../challenge/dataset/build_d3_wave1_plan.py#L408)。类型：`FunctionDef`。

```python
main.pool(bucket: str) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main.allocation_key`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 504 行](../../../challenge/dataset/build_d3_wave1_plan.py#L504)。类型：`FunctionDef`。

```python
main.allocation_key(row: dict[str, Any], bucket: str) -> tuple
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main.allocate`

源码位置：[challenge/dataset/build_d3_wave1_plan.py 第 528 行](../../../challenge/dataset/build_d3_wave1_plan.py#L528)。类型：`FunctionDef`。

```python
main.allocate(bucket: str, target: int) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `canonical_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(raw).hexdigest`, `json.dumps`, `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode`.
- `load_json` 调用：`json.loads`, `path.read_text`.
- `load_jsonl` 调用：`json.loads`, `line.strip`, `path.open`, `rows.append`.
- `row_family` 调用：`row.get`, `str`.
- `row_source` 调用：`row.get`, `str`.
- `plan_seed_values` 调用：`RuntimeError`, `isinstance`, `out.add`, `payload.get`, `row.get`, `set`.
- `validate_teacher_manifest` 调用：`RuntimeError`, `load_json`, `verification.get`, `x.get`.
- `main` 调用：`Counter`, `Path`, `QUOTAS.items`, `RuntimeError`, `allocate`, `allocation_key`, `argparse.ArgumentParser`, `args.d2_split_assignments.resolve`, `args.d2_split_report.resolve`, `args.d2_wave2_plan.resolve`, `args.output_root.resolve`, `args.teacher_manifest.resolve`, `args.wave1_plan.resolve`, `bucket_alloc.items`, `canonical_sha256`, `copy.deepcopy`, `counter.items`, `counts.get`, `d2_wave2.get`, `dict`, `isinstance`, `json.dumps`, `len`, `list`, `load_json`, `load_jsonl`, `max`, `min`, `new_row.get`, `new_row.pop`, `output_path.write_text`, `output_root.mkdir`, `p.is_file`, `parser.add_argument`, `parser.parse_args`, `plan.append`, `plan_seed_values`, `pool`, `print`, `range`, `row.get`, `row_family`, `row_source`, `scenario_counts.items`, `scenario_counts.values`, `set`, `sha256_file`, `sorted`, `split_report.get`, `str`, `subprocess.check_output`, `subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip`, `sum`, `tags.add`, `template_by_scenario.setdefault`, `template_by_scenario.values`, `train_hn_count.items`, `validate_teacher_manifest`, `x.get`.
- `pool` 调用：`RuntimeError`, `row_family`, `row_source`, `str`.
- `allocation_key` 调用：`row_family`, `str`.
- `allocate` 调用：`RuntimeError`, `allocation_key`, `copy.deepcopy`, `len`, `min`, `new_row.get`, `new_row.pop`, `plan.append`, `pool`, `set`, `sorted`, `str`, `tags.add`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `allocate`，第 551 行：`RuntimeError(f'capacity exhausted while allocating {bucket}: made={made} target={target}')`。
- `main`，第 250 行：`RuntimeError(f'required input missing: {p}')`。
- `main`，第 260 行：`RuntimeError(f"unexpected D2 split version: {split_report.get('split_version')!r}")`。
- `main`，第 266 行：`RuntimeError('D2 split report is not PASS')`。
- `main`，第 276 行：`RuntimeError('D2 governed baseline counts do not match frozen D2 delivery')`。
- `main`，第 281 行：`RuntimeError(f'expected 3600 D2 assignments, got {len(assignments)}')`。
- `main`，第 304 行：`RuntimeError(f'D2 split baseline mismatch: {len(train)}/{len(val)}/{len(reserved)}')`。
- `main`，第 325 行：`RuntimeError('D2 Wave2 formal plan must contain exactly 2000 rows')`。
- `main`，第 335 行：`RuntimeError('D2 Wave2 row missing scenario_id')`。
- `main`，第 341 行：`RuntimeError(f'expected 101 D2 Wave2 template scenarios, got {len(template_by_scenario)}')`。
- `main`，第 359 行：`RuntimeError(f'D3 Wave1 seed namespace collides with D2: {sorted(collision)[:20]}')`。
- `main`，第 369 行：`RuntimeError(f'D3 Wave1 seed namespace invalid: {min(namespace)}..{max(namespace)} count={len(namespace)} expected={SEED_START}..{SEED_START + PLANNED_RUNS - 1} count={PLANNED_RUNS}')`。
- `main`，第 404 行：`RuntimeError('no historical hard-negative scenarios available')`。
- `main`，第 446 行：`RuntimeError(f'unknown D3 bucket: {bucket}')`。
- `main`，第 479 行：`RuntimeError(f'empty candidate pool for {bucket}')`。
- `main`，第 484 行：`RuntimeError(f'insufficient nominal capacity for {bucket}: target={target} capacity={capacity} scenarios={len(p)}')`。
- `main`，第 551 行：`RuntimeError(f'capacity exhausted while allocating {bucket}: made={made} target={target}')`。
- `main`，第 628 行：`RuntimeError(f'expected 2000 D3 Wave1 rows, got {len(plan)}')`。
- `main`，第 642 行：`RuntimeError('D3 Wave1 seeds are not exact contiguous namespace')`。
- `main`，第 652 行：`RuntimeError('duplicate D3 extension_id')`。
- `main`，第 660 行：`RuntimeError(f'D3 quota mismatch: actual={dict(bucket_counts)} expected={QUOTAS}')`。
- `main`，第 672 行：`RuntimeError('D3 per-scenario global cap violated')`。
- `main`，第 685 行：`RuntimeError('D2 reserved-test candidate group count mismatch')`。
- `plan_seed_values`，第 134 行：`RuntimeError('prior plan has no plan[]')`。
- `pool`，第 446 行：`RuntimeError(f'unknown D3 bucket: {bucket}')`。
- `validate_teacher_manifest`，第 151 行：`RuntimeError(f"Teacher profile mismatch: {x.get('teacher_profile')!r}")`。
- `validate_teacher_manifest`，第 157 行：`RuntimeError(f"Teacher SHA mismatch: {x.get('teacher_git_sha')!r}")`。
- `validate_teacher_manifest`，第 165 行：`RuntimeError('Teacher v4 directional semantic gate is not frozen PASS')`。
- `validate_teacher_manifest`，第 173 行：`RuntimeError('Teacher v4 directional closed-loop gate is not frozen PASS')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 183 行：`parser.add_argument('--d2-wave2-plan', type=Path, default=Path('artifacts/b1_d2_expansion_plan_wave2_v1/d2_expansion_plan_wave2.json'))`。
- 第 192 行：`parser.add_argument('--d2-split-assignments', type=Path, default=Path('artifacts/b1_d2_split_v1/split_assignments.jsonl'))`。
- 第 201 行：`parser.add_argument('--d2-split-report', type=Path, default=Path('artifacts/b1_d2_split_v1/split_report.json'))`。
- 第 210 行：`parser.add_argument('--wave1-plan', type=Path, required=True, help='Frozen D2 Wave1 formal plan')`。
- 第 217 行：`parser.add_argument('--teacher-manifest', type=Path, default=Path('challenge/teacher_pinned_manifest_v4.json'))`。
- 第 225 行：`parser.add_argument('--output-root', type=Path, default=Path('artifacts/b1_d3_expansion_plan_wave1_v1'))`。

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

### `challenge/dataset/build_d3_wave1_plan.py`

来源 SHA256：`ce7973b221c4398567605540e207daa911ed461b00cd71bddd9ffef5a005d26a`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 183 | `'--d2-wave2-plan'` | `type=Path; default=Path('artifacts/b1_d2_expansion_plan_wave2_v1/d2_expansion_plan_wave2.json')` |
| 192 | `'--d2-split-assignments'` | `type=Path; default=Path('artifacts/b1_d2_split_v1/split_assignments.jsonl')` |
| 201 | `'--d2-split-report'` | `type=Path; default=Path('artifacts/b1_d2_split_v1/split_report.json')` |
| 210 | `'--wave1-plan'` | `type=Path; required=True; help='Frozen D2 Wave1 formal plan'` |
| 217 | `'--teacher-manifest'` | `type=Path; default=Path('challenge/teacher_pinned_manifest_v4.json')` |
| 225 | `'--output-root'` | `type=Path; default=Path('artifacts/b1_d3_expansion_plan_wave1_v1')` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `plan_seed_values` / 134 | `not isinstance(rows, list)` | `raise RuntimeError('prior plan has no plan[]')` |
| `validate_teacher_manifest` / 151 | `x.get('teacher_profile') != EXPECTED_TEACHER_PROFILE` | `raise RuntimeError(f"Teacher profile mismatch: {x.get('teacher_profile')!r}")` |
| `validate_teacher_manifest` / 157 | `x.get('teacher_git_sha') != EXPECTED_TEACHER_GIT_SHA` | `raise RuntimeError(f"Teacher SHA mismatch: {x.get('teacher_git_sha')!r}")` |
| `validate_teacher_manifest` / 165 | `verification.get('directional_semantic_gate') != '8/8 PASS'` | `raise RuntimeError('Teacher v4 directional semantic gate is not frozen PASS')` |
| `validate_teacher_manifest` / 173 | `verification.get('directional_closed_loop_gate') != '8/8 SUCCEEDED'` | `raise RuntimeError('Teacher v4 directional closed-loop gate is not frozen PASS')` |
| `main` / 250 | `not p.is_file()` | `raise RuntimeError(f'required input missing: {p}')` |
| `main` / 260 | `split_report.get('split_version') != EXPECTED_D2_SPLIT_VERSION` | `raise RuntimeError(f"unexpected D2 split version: {split_report.get('split_version')!r}")` |
| `main` / 266 | `split_report.get('status') != 'PASS'` | `raise RuntimeError('D2 split report is not PASS')` |
| `main` / 276 | `counts.get('governed_assets') != 3600 or counts.get('positive') != 3395 or counts.get('hard_negative') != 205 or (counts.get('excluded') != 192)` | `raise RuntimeError('D2 governed baseline counts do not match frozen D2 delivery')` |
| `main` / 281 | `len(assignments) != 3600` | `raise RuntimeError(f'expected 3600 D2 assignments, got {len(assignments)}')` |
| `main` / 304 | `(len(train), len(val), len(reserved)) != (2520, 540, 540)` | `raise RuntimeError(f'D2 split baseline mismatch: {len(train)}/{len(val)}/{len(reserved)}')` |
| `main` / 325 | `not isinstance(prior_rows, list) or len(prior_rows) != 2000` | `raise RuntimeError('D2 Wave2 formal plan must contain exactly 2000 rows')` |
| `main` / 335 | `not sid` | `raise RuntimeError('D2 Wave2 row missing scenario_id')` |
| `main` / 341 | `len(template_by_scenario) != 101` | `raise RuntimeError(f'expected 101 D2 Wave2 template scenarios, got {len(template_by_scenario)}')` |
| `main` / 359 | `collision` | `raise RuntimeError(f'D3 Wave1 seed namespace collides with D2: {sorted(collision)[:20]}')` |
| `main` / 369 | `min(namespace) != SEED_START or max(namespace) != SEED_START + PLANNED_RUNS - 1 or len(namespace) != PLANNED_RUNS` | `raise RuntimeError(f'D3 Wave1 seed namespace invalid: {min(namespace)}..{max(namespace)} count={len(namespace)} expected={SEED_START}..{SEED_START + PLANNED_RUNS - 1} count={PLANNED_RUNS}')` |
| `main` / 404 | `not hn_target_ids` | `raise RuntimeError('no historical hard-negative scenarios available')` |
| `main` / 479 | `not p` | `raise RuntimeError(f'empty candidate pool for {bucket}')` |
| `main` / 484 | `capacity < target` | `raise RuntimeError(f'insufficient nominal capacity for {bucket}: target={target} capacity={capacity} scenarios={len(p)}')` |
| `main` / 628 | `len(plan) != 2000` | `raise RuntimeError(f'expected 2000 D3 Wave1 rows, got {len(plan)}')` |
| `main` / 642 | `seeds != expected_seeds` | `raise RuntimeError('D3 Wave1 seeds are not exact contiguous namespace')` |
| `main` / 652 | `len(extension_ids) != len(set(extension_ids))` | `raise RuntimeError('duplicate D3 extension_id')` |
| `main` / 660 | `dict(bucket_counts) != QUOTAS` | `raise RuntimeError(f'D3 quota mismatch: actual={dict(bucket_counts)} expected={QUOTAS}')` |
| `main` / 672 | `max(scenario_counts.values()) > global_cap` | `raise RuntimeError('D3 per-scenario global cap violated')` |
| `main` / 685 | `len(reserved_group_keys) != 540` | `raise RuntimeError('D2 reserved-test candidate group count mismatch')` |
| `main.pool` / 446 | `本地无直接if；检查上下文` | `raise RuntimeError(f'unknown D3 bucket: {bucket}')` |
| `main.allocate` / 551 | `not eligible` | `raise RuntimeError(f'capacity exhausted while allocating {bucket}: made={made} target={target}')` |

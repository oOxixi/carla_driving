# build_d2_expansion_plan：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d2_expansion_plan.py](../../../challenge/dataset/build_d2_expansion_plan.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d2_expansion_plan

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `scenario_file_path`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 30 行](../../../challenge/dataset/build_d2_expansion_plan.py#L30)。类型：`FunctionDef`。

```python
scenario_file_path(repo: Path, row: dict[str, str]) -> Path
```

`scenario_file_path` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `seed_expansion_policy`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 37 行](../../../challenge/dataset/build_d2_expansion_plan.py#L37)。类型：`FunctionDef`。

```python
seed_expansion_policy(repo: Path, row: dict[str, str]) -> tuple[bool, str]
```

Return whether arbitrary D2 extension-seed expansion is safe.

Route-generalization destination scenarios are fixed Route Manager
regression fixtures. carla_runner gives --seed structural semantics
by binding it to spawn_index, so arbitrary extension seeds can mutate
their start/route topology while leaving their authored destination
and distance contracts unchanged.

These fixtures remain valid benchmark/regression scenarios, but they
are not valid sources for arbitrary-seed Teacher acquisition.

### `canonical_json_sha256`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 164 行](../../../challenge/dataset/build_d2_expansion_plan.py#L164)。类型：`FunctionDef`。

```python
canonical_json_sha256(value: Any) -> str
```

`canonical_json_sha256` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `read_registry`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 172 行](../../../challenge/dataset/build_d2_expansion_plan.py#L172)。类型：`FunctionDef`。

```python
read_registry(path: Path) -> list[dict[str, str]]
```

`read_registry` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `scenario_exists`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 185 行](../../../challenge/dataset/build_d2_expansion_plan.py#L185)。类型：`FunctionDef`。

```python
scenario_exists(repo: Path, rel: str) -> bool
```

`scenario_exists` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `load_prior_seed_values`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 190 行](../../../challenge/dataset/build_d2_expansion_plan.py#L190)。类型：`FunctionDef`。

```python
load_prior_seed_values(repo: Path, prior_plan_path: Path) -> set[int]
```

`load_prior_seed_values` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `cap_for`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 203 行](../../../challenge/dataset/build_d2_expansion_plan.py#L203)。类型：`FunctionDef`。

```python
cap_for(row: dict[str, str]) -> int
```

`cap_for` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `historical_status`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 218 行](../../../challenge/dataset/build_d2_expansion_plan.py#L218)。类型：`FunctionDef`。

```python
historical_status(sid: str) -> str
```

`historical_status` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `tags_for`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 228 行](../../../challenge/dataset/build_d2_expansion_plan.py#L228)。类型：`FunctionDef`。

```python
tags_for(row: dict[str, str]) -> list[str]
```

`tags_for` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `candidate_pool`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 244 行](../../../challenge/dataset/build_d2_expansion_plan.py#L244)。类型：`FunctionDef`。

```python
candidate_pool(repo: Path, rows: list[dict[str, str]], bucket: str) -> list[dict[str, str]]
```

`candidate_pool` 参与分组、候选或确定性切分与分配；必须保持同组不跨split、seed可复现并记录未满足配额，不能靠重跑挑选有利结果。

### `build_plan`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 271 行](../../../challenge/dataset/build_d2_expansion_plan.py#L271)。类型：`FunctionDef`。

```python
build_plan(repo: Path, rows: list[dict[str, str]], prior_seeds: set[int]) -> list[dict[str, Any]]
```

`build_plan` 从显式输入构造版本化样本、计划、清单或派生视图；保持原始记录不变，并把默认、排除原因与来源身份写入新产物。

### `build_plan.allocate`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 300 行](../../../challenge/dataset/build_d2_expansion_plan.py#L300)。类型：`FunctionDef`。

```python
build_plan.allocate(bucket: str, target: int) -> None
```

`allocate` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `main`

源码位置：[challenge/dataset/build_d2_expansion_plan.py 第 401 行](../../../challenge/dataset/build_d2_expansion_plan.py#L401)。类型：`FunctionDef`。

```python
main() -> int
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `scenario_file_path` 调用：`Path`.
- `seed_expansion_policy` 调用：`json.loads`, `path.read_text`, `payload.get`, `route.get`, `scenario_file_path`, `str`, `str(route.get('planning_mode', '')).strip`, `str(tag).strip`.
- `canonical_json_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(raw).hexdigest`, `json.dumps`, `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode`.
- `read_registry` 调用：`RuntimeError`, `csv.DictReader`, `list`, `path.open`, `required.issubset`, `sorted`.
- `scenario_exists` 调用：`(repo / 'scenarios' / p).is_file`, `(repo / p).is_file`, `Path`.
- `load_prior_seed_values` 调用：`RuntimeError`, `isinstance`, `json.loads`, `prior.get`, `prior_plan_path.read_text`, `row.get`, `set`, `values.add`.
- `cap_for` 调用：`row.get`.
- `tags_for` 调用：`ACTION_TAGS.get`, `list`, `row.get`, `set`, `sorted`, `tags.append`.
- `candidate_pool` 调用：`RuntimeError`, `r.get`, `seed_expansion_policy`.
- `build_plan` 调用：`AssertionError`, `Counter`, `QUOTAS.items`, `RuntimeError`, `allocate`, `candidate_pool`, `cap_for`, `historical_status`, `int`, `json.dumps`, `len`, `plan.append`, `print`, `r.get`, `set`, `sorted`, `str`, `str(row['seed']).strip`, `sum`, `tags_for`.
- `main` 调用：`'|'.join`, `(repo / args.output_dir).resolve`, `(repo / args.prior_d1_plan).resolve`, `(repo / args.registry).resolve`, `Counter`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `any`, `ap.add_argument`, `ap.parse_args`, `argparse.ArgumentParser`, `base.current_branch`, `base.current_head`, `base.sha256_file`, `base.verify_tracked_file_matches_head`, `base.write_json`, `bucket_counts.get`, `bucket_counts.items`, `build_plan`, `canonical_json_sha256`, `cap_for`, `csv.DictWriter`, `dict`, `family_counts.items`, `history_counts.items`, `json.dumps`, `len`, `load_prior_seed_values`, `map_counts.items`, `max`, `next`, `normalized_bucket_counts.items`, `output_dir.mkdir`, `p.is_file`, `plan_csv.open`, `print`, `prior_plan_path.relative_to`, `r.get`, `read_registry`, `registry_path.relative_to`, `report.write_text`, `scenario_counts.items`, `scenario_counts.values`, `scenario_exists`, `seed_expansion_policy`, `seed_expansion_policy_counts.items`, `set`, `sorted`, `source_counts.items`, `str`, `w.writeheader`, `w.writerow`.
- `allocate` 调用：`AssertionError`, `RuntimeError`, `candidate_pool`, `cap_for`, `historical_status`, `int`, `len`, `plan.append`, `r.get`, `sorted`, `str`, `str(row['seed']).strip`, `tags_for`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `allocate`，第 315 行：`RuntimeError(f'empty candidate pool for {bucket}')`。
- `allocate`，第 334 行：`RuntimeError(f'cannot satisfy quota {bucket}: target={target} made={made}')`。
- `allocate`，第 348 行：`AssertionError('seed collision')`。
- `build_plan`，第 293 行：`RuntimeError(f'raw capacity insufficient for {bucket}: target={target} capacity={capacity} scenarios={len(pool)}')`。
- `build_plan`，第 315 行：`RuntimeError(f'empty candidate pool for {bucket}')`。
- `build_plan`，第 334 行：`RuntimeError(f'cannot satisfy quota {bucket}: target={target} made={made}')`。
- `build_plan`，第 348 行：`AssertionError('seed collision')`。
- `build_plan`，第 387 行：`RuntimeError(f'planned run count mismatch: {len(plan)}')`。
- `build_plan`，第 392 行：`RuntimeError('duplicate extension_seed')`。
- `build_plan`，第 394 行：`RuntimeError('duplicate extension_id')`。
- `build_plan`，第 396 行：`RuntimeError('D2 seed overlaps prior D1 extension')`。
- `candidate_pool`，第 268 行：`RuntimeError(f'unknown quota bucket {bucket}')`。
- `load_prior_seed_values`，第 194 行：`RuntimeError('prior D1 extension plan missing plan[]')`。
- `main`，第 426 行：`RuntimeError(f'required file missing: {p}')`。
- `main`，第 430 行：`RuntimeError(f'registry SHA mismatch expected={EXPECTED_REGISTRY_SHA256} actual={registry_sha}')`。
- `main`，第 436 行：`RuntimeError(f'prior D1 plan SHA mismatch expected={EXPECTED_PRIOR_D1_PLAN_SHA256} actual={prior_plan_sha}')`。
- `main`，第 462 行：`RuntimeError('UNSEEN appears inside TRAIN_POSITIVE registry rows')`。
- `main`，第 464 行：`RuntimeError('reserved Test row leaked into TRAIN_POSITIVE')`。
- `main`，第 471 行：`RuntimeError(f'scenario files missing: {missing_files[:20]}')`。
- `main`，第 495 行：`RuntimeError(f'quota mismatch expected={QUOTAS} actual={normalized_bucket_counts} unexpected={unexpected_buckets}')`。
- `main`，第 504 行：`RuntimeError(f'scenario cap exceeded: {sid} {count}>{cap_for(row)}')`。
- `read_registry`，第 181 行：`RuntimeError(f'registry schema mismatch: {sorted(rows[0] if rows else [])}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 403 行：`ap.add_argument('--registry', default='artifacts/b1_d1_registry_final/scenario_registry_v3.csv')`。
- 第 407 行：`ap.add_argument('--prior-d1-plan', default='artifacts/b1_d1_extension_plan/d1_extension_plan_formal_v2.json')`。
- 第 411 行：`ap.add_argument('--output-dir', default='artifacts/b1_d2_expansion_plan_v2')`。
- 第 415 行：`ap.add_argument('--dry-run', action='store_true')`。
- 第 416 行：`ap.add_argument('--allow-uncommitted-code', action='store_true')`。

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

### `challenge/dataset/build_d2_expansion_plan.py`

来源 SHA256：`f829a9d7ff1bbffe831617cb704d4743695dd44ffd0ced8b14f68cacfbd4c59a`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 403 | `'--registry'` | `default='artifacts/b1_d1_registry_final/scenario_registry_v3.csv'` |
| 407 | `'--prior-d1-plan'` | `default='artifacts/b1_d1_extension_plan/d1_extension_plan_formal_v2.json'` |
| 411 | `'--output-dir'` | `default='artifacts/b1_d2_expansion_plan_v2'` |
| 415 | `'--dry-run'` | `action='store_true'` |
| 416 | `'--allow-uncommitted-code'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_registry` / 181 | `not rows or not required.issubset(rows[0])` | `raise RuntimeError(f'registry schema mismatch: {sorted(rows[0] if rows else [])}')` |
| `load_prior_seed_values` / 194 | `not isinstance(rows, list)` | `raise RuntimeError('prior D1 extension plan missing plan[]')` |
| `candidate_pool` / 268 | `本地无直接if；检查上下文` | `raise RuntimeError(f'unknown quota bucket {bucket}')` |
| `build_plan` / 293 | `capacity < target` | `raise RuntimeError(f'raw capacity insufficient for {bucket}: target={target} capacity={capacity} scenarios={len(pool)}')` |
| `build_plan` / 387 | `len(plan) != PLANNED_RUNS` | `raise RuntimeError(f'planned run count mismatch: {len(plan)}')` |
| `build_plan` / 392 | `len(seeds) != len(set(seeds))` | `raise RuntimeError('duplicate extension_seed')` |
| `build_plan` / 394 | `len(ids) != len(set(ids))` | `raise RuntimeError('duplicate extension_id')` |
| `build_plan` / 396 | `set(seeds) & prior_seeds` | `raise RuntimeError('D2 seed overlaps prior D1 extension')` |
| `build_plan.allocate` / 315 | `not pool` | `raise RuntimeError(f'empty candidate pool for {bucket}')` |
| `build_plan.allocate` / 334 | `cursor >= len(pool) AND stalled_rounds > len(pool) + 2` | `raise RuntimeError(f'cannot satisfy quota {bucket}: target={target} made={made}')` |
| `build_plan.allocate` / 348 | `next_seed in prior_seeds` | `raise AssertionError('seed collision')` |
| `main` / 426 | `not p.is_file()` | `raise RuntimeError(f'required file missing: {p}')` |
| `main` / 430 | `registry_sha != EXPECTED_REGISTRY_SHA256` | `raise RuntimeError(f'registry SHA mismatch expected={EXPECTED_REGISTRY_SHA256} actual={registry_sha}')` |
| `main` / 436 | `prior_plan_sha != EXPECTED_PRIOR_D1_PLAN_SHA256` | `raise RuntimeError(f'prior D1 plan SHA mismatch expected={EXPECTED_PRIOR_D1_PLAN_SHA256} actual={prior_plan_sha}')` |
| `main` / 462 | `any((r['source_bucket'] == 'UNSEEN' for r in train_positive))` | `raise RuntimeError('UNSEEN appears inside TRAIN_POSITIVE registry rows')` |
| `main` / 464 | `any(('RESERVED_TEST' in r.get('policy_class', '') for r in train_positive))` | `raise RuntimeError('reserved Test row leaked into TRAIN_POSITIVE')` |
| `main` / 471 | `missing_files` | `raise RuntimeError(f'scenario files missing: {missing_files[:20]}')` |
| `main` / 495 | `normalized_bucket_counts != QUOTAS or unexpected_buckets` | `raise RuntimeError(f'quota mismatch expected={QUOTAS} actual={normalized_bucket_counts} unexpected={unexpected_buckets}')` |
| `main` / 504 | `count > cap_for(row)` | `raise RuntimeError(f'scenario cap exceeded: {sid} {count}>{cap_for(row)}')` |

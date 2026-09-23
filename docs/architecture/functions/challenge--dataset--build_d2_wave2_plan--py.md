# build_d2_wave2_plan：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d2_wave2_plan.py](../../../challenge/dataset/build_d2_wave2_plan.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d2_wave2_plan

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `canonical_json_sha256`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 132 行](../../../challenge/dataset/build_d2_wave2_plan.py#L132)。类型：`FunctionDef`。

```python
canonical_json_sha256(value: object) -> str
```

`canonical_json_sha256` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `sha256_file`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 143 行](../../../challenge/dataset/build_d2_wave2_plan.py#L143)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `scenario_file_path`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 151 行](../../../challenge/dataset/build_d2_wave2_plan.py#L151)。类型：`FunctionDef`。

```python
scenario_file_path(repo: Path, row: dict[str, str]) -> Path
```

`scenario_file_path` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `scenario_exists`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 158 行](../../../challenge/dataset/build_d2_wave2_plan.py#L158)。类型：`FunctionDef`。

```python
scenario_exists(repo: Path, rel: str) -> bool
```

`scenario_exists` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `seed_expansion_policy`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 163 行](../../../challenge/dataset/build_d2_wave2_plan.py#L163)。类型：`FunctionDef`。

```python
seed_expansion_policy(repo: Path, row: dict[str, str]) -> tuple[bool, str]
```

`seed_expansion_policy` 参与分组、候选或确定性切分与分配；必须保持同组不跨split、seed可复现并记录未满足配额，不能靠重跑挑选有利结果。

### `read_registry`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 192 行](../../../challenge/dataset/build_d2_wave2_plan.py#L192)。类型：`FunctionDef`。

```python
read_registry(path: Path) -> list[dict[str, str]]
```

`read_registry` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `load_plan_seed_values`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 215 行](../../../challenge/dataset/build_d2_wave2_plan.py#L215)。类型：`FunctionDef`。

```python
load_plan_seed_values(path: Path) -> set[int]
```

`load_plan_seed_values` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `validate_wave1_plan`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 232 行](../../../challenge/dataset/build_d2_wave2_plan.py#L232)。类型：`FunctionDef`。

```python
validate_wave1_plan(path: Path) -> dict[str, Any]
```

`validate_wave1_plan` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `validate_teacher_manifest`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 285 行](../../../challenge/dataset/build_d2_wave2_plan.py#L285)。类型：`FunctionDef`。

```python
validate_teacher_manifest(path: Path) -> dict[str, Any]
```

`validate_teacher_manifest` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `validate_semantic_report`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 313 行](../../../challenge/dataset/build_d2_wave2_plan.py#L313)。类型：`FunctionDef`。

```python
validate_semantic_report(path: Path) -> dict[str, Any]
```

`validate_semantic_report` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `validate_eligibility_report`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 336 行](../../../challenge/dataset/build_d2_wave2_plan.py#L336)。类型：`FunctionDef`。

```python
validate_eligibility_report(path: Path) -> dict[str, Any]
```

`validate_eligibility_report` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `cap_for`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 359 行](../../../challenge/dataset/build_d2_wave2_plan.py#L359)。类型：`FunctionDef`。

```python
cap_for(row: dict[str, str], bucket: str) -> int
```

`cap_for` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `historical_status`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 388 行](../../../challenge/dataset/build_d2_wave2_plan.py#L388)。类型：`FunctionDef`。

```python
historical_status(sid: str) -> str
```

`historical_status` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `tags_for`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 401 行](../../../challenge/dataset/build_d2_wave2_plan.py#L401)。类型：`FunctionDef`。

```python
tags_for(row: dict[str, str], bucket: str) -> list[str]
```

`tags_for` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `base_allowed`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 429 行](../../../challenge/dataset/build_d2_wave2_plan.py#L429)。类型：`FunctionDef`。

```python
base_allowed(repo: Path, rows: list[dict[str, str]]) -> list[dict[str, str]]
```

`base_allowed` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `candidate_pool`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 443 行](../../../challenge/dataset/build_d2_wave2_plan.py#L443)。类型：`FunctionDef`。

```python
candidate_pool(repo: Path, rows: list[dict[str, str]], bucket: str) -> list[dict[str, str]]
```

`candidate_pool` 参与分组、候选或确定性切分与分配；必须保持同组不跨split、seed可复现并记录未满足配额，不能靠重跑挑选有利结果。

### `build_plan`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 495 行](../../../challenge/dataset/build_d2_wave2_plan.py#L495)。类型：`FunctionDef`。

```python
build_plan(repo: Path, rows: list[dict[str, str]], prior_seeds: set[int]) -> tuple[list[dict[str, Any]], dict[str, Any]]
```

`build_plan` 从显式输入构造版本化样本、计划、清单或派生视图；保持原始记录不变，并把默认、排除原因与来源身份写入新产物。

### `build_plan.allocate`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 544 行](../../../challenge/dataset/build_d2_wave2_plan.py#L544)。类型：`FunctionDef`。

```python
build_plan.allocate(bucket: str, target: int) -> None
```

`allocate` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `main`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 695 行](../../../challenge/dataset/build_d2_wave2_plan.py#L695)。类型：`FunctionDef`。

```python
main() -> int
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

### `main.resolve_arg`

源码位置：[challenge/dataset/build_d2_wave2_plan.py 第 713 行](../../../challenge/dataset/build_d2_wave2_plan.py#L713)。类型：`FunctionDef`。

```python
main.resolve_arg(raw: str) -> Path
```

`resolve_arg` 处理运行环境、仓库或路径边界；其结果用于可复现性与失败清理，不等同于样本质量或发布Gate。

## 内部调用与异常路径

- `canonical_json_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(raw).hexdigest`, `json.dumps`, `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode`.
- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `scenario_file_path` 调用：`Path`.
- `scenario_exists` 调用：`(repo / 'scenarios' / p).is_file`, `(repo / p).is_file`, `Path`.
- `seed_expansion_policy` 调用：`json.loads`, `path.read_text`, `payload.get`, `route.get`, `scenario_file_path`, `str`, `str(route.get('planning_mode', '')).strip`, `str(tag).strip`.
- `read_registry` 调用：`RuntimeError`, `csv.DictReader`, `list`, `path.open`, `required.issubset`, `sorted`.
- `load_plan_seed_values` 调用：`RuntimeError`, `isinstance`, `json.loads`, `path.read_text`, `payload.get`, `row.get`, `seeds.add`, `set`.
- `validate_wave1_plan` 调用：`RuntimeError`, `any`, `canonical_json_sha256`, `clone.pop`, `dict`, `isinstance`, `json.loads`, `len`, `max`, `min`, `path.read_text`, `payload.get`, `row.get`, `set`, `type`.
- `validate_teacher_manifest` 调用：`RuntimeError`, `json.loads`, `path.read_text`, `verification.get`, `x.get`.
- `validate_semantic_report` 调用：`RuntimeError`, `json.loads`, `path.read_text`, `x.get`.
- `validate_eligibility_report` 调用：`RuntimeError`, `json.loads`, `path.read_text`, `x.get`.
- `cap_for` 调用：`row.get`.
- `tags_for` 调用：`ACTION_TAGS.get`, `list`, `row.get`, `set`, `sorted`, `tags.append`, `tags.extend`.
- `base_allowed` 调用：`seed_expansion_policy`.
- `candidate_pool` 调用：`RuntimeError`, `base_allowed`, `row.get`.
- `build_plan` 调用：`Counter`, `QUOTAS.items`, `RuntimeError`, `allocate`, `candidate_pool`, `cap_for`, `dict`, `historical_status`, `int`, `json.dumps`, `len`, `list`, `plan.append`, `print`, `range`, `recollection_counts.items`, `row.get`, `set`, `sorted`, `str`, `str(row['seed']).strip`, `sum`, `tags_for`.
- `main` 调用：`'|'.join`, `Counter`, `Path`, `Path(__file__).resolve`, `Path(raw).expanduser`, `RuntimeError`, `any`, `ap.add_argument`, `ap.parse_args`, `argparse.ArgumentParser`, `base.current_branch`, `base.current_head`, `base.verify_tracked_file_matches_head`, `base.write_json`, `bucket_counts.get`, `bucket_counts.items`, `build_plan`, `builder_identity.get`, `canonical_json_sha256`, `csv.DictWriter`, `dict`, `eligibility_report.get`, `family_counts.items`, `history_counts.items`, `isinstance`, `json.dumps`, `len`, `load_plan_seed_values`, `map_counts.items`, `max`, `normalized_bucket_counts.items`, `output_dir.mkdir`, `p.is_absolute`, `p.resolve`, `path.is_file`, `plan_csv.open`, `policy_counts.items`, `print`, `read_registry`, `recollection_counts.items`, `report.write_text`, `resolve_arg`, `row.get`, `scenario_counts.values`, `scenario_exists`, `seed_expansion_policy`, `semantic_report.get`, `sha256_file`, `sorted`, `source_counts.items`, `str`, `teacher_manifest.get`, `validate_eligibility_report`, `validate_semantic_report`, `validate_teacher_manifest`, `validate_wave1_plan`, `writer.writeheader`, `writer.writerow`.
- `allocate` 调用：`RuntimeError`, `candidate_pool`, `cap_for`, `historical_status`, `int`, `len`, `plan.append`, `row.get`, `sorted`, `str`, `str(row['seed']).strip`, `tags_for`.
- `resolve_arg` 调用：`Path`, `Path(raw).expanduser`, `p.is_absolute`, `p.resolve`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `allocate`，第 560 行：`RuntimeError(f'empty candidate pool for {bucket}')`。
- `allocate`，第 582 行：`RuntimeError(f'cannot satisfy quota {bucket}: target={target} made={made}')`。
- `allocate`，第 598 行：`RuntimeError('Wave2 seed namespace exhausted')`。
- `allocate`，第 601 行：`RuntimeError(f'unexpected prior seed collision: {next_seed}')`。
- `build_plan`，第 507 行：`RuntimeError(f'Wave2 reserved seed namespace overlaps prior acquisition: {sorted(collision)[:20]}')`。
- `build_plan`，第 529 行：`RuntimeError(f'raw capacity insufficient for {bucket}: target={target} capacity={capacity} scenarios={len(pool)}')`。
- `build_plan`，第 560 行：`RuntimeError(f'empty candidate pool for {bucket}')`。
- `build_plan`，第 582 行：`RuntimeError(f'cannot satisfy quota {bucket}: target={target} made={made}')`。
- `build_plan`，第 598 行：`RuntimeError('Wave2 seed namespace exhausted')`。
- `build_plan`，第 601 行：`RuntimeError(f'unexpected prior seed collision: {next_seed}')`。
- `build_plan`，第 650 行：`RuntimeError(f'planned run count mismatch: {len(plan)}')`。
- `build_plan`，第 658 行：`RuntimeError('duplicate extension_seed')`。
- `build_plan`，第 661 行：`RuntimeError('duplicate extension_id')`。
- `build_plan`，第 664 行：`RuntimeError('Wave2 seed overlaps prior acquisition')`。
- `build_plan`，第 667 行：`RuntimeError(f'Wave2 seeds must exactly occupy reserved namespace {SEED_START}..{SEED_START + PLANNED_RUNS - 1}')`。
- `build_plan`，第 687 行：`RuntimeError(f'directional recollection must be exactly balanced 30/scenario: {dict(sorted(recollection_counts.items()))}')`。
- `candidate_pool`，第 492 行：`RuntimeError(f'unknown quota bucket {bucket}')`。
- `load_plan_seed_values`，第 220 行：`RuntimeError(f'plan[] missing: {path}')`。
- `main`，第 738 行：`RuntimeError(f'required file missing: {path}')`。
- `main`，第 743 行：`RuntimeError(f'registry SHA mismatch expected={EXPECTED_REGISTRY_SHA256} actual={registry_sha}')`。
- `main`，第 752 行：`RuntimeError(f'prior D1 plan SHA mismatch expected={EXPECTED_PRIOR_D1_PLAN_SHA256} actual={prior_d1_sha}')`。
- `main`，第 803 行：`RuntimeError('UNSEEN appears inside TRAIN_POSITIVE registry rows')`。
- `main`，第 811 行：`RuntimeError('reserved Test row leaked into TRAIN_POSITIVE')`。
- `main`，第 822 行：`RuntimeError(f'scenario files missing: {missing_files[:20]}')`。
- `main`，第 836 行：`RuntimeError(f'directional recollection sources missing from TRAIN_POSITIVE registry: {sorted(missing_directional)}')`。
- `main`，第 850 行：`RuntimeError('historical D1/Wave1 seed collision detected')`。
- `main`，第 887 行：`RuntimeError(f'quota mismatch expected={QUOTAS} actual={normalized_bucket_counts}')`。
- `read_registry`，第 208 行：`RuntimeError(f'registry schema mismatch: {sorted(rows[0] if rows else [])}')`。
- `validate_eligibility_report`，第 346 行：`RuntimeError('training eligibility report schema mismatch')`。
- `validate_eligibility_report`，第 351 行：`RuntimeError(f'unexpected eligibility counts: D1={d1} D2={d2} HN={hn} cumulative={cumulative}')`。
- `validate_semantic_report`，第 323 行：`RuntimeError('semantic governance report schema mismatch')`。
- `validate_semantic_report`，第 328 行：`RuntimeError(f'unexpected semantic quarantine counts: D1={d1} D2={d2} TOTAL={total}')`。
- `validate_teacher_manifest`，第 289 行：`RuntimeError(f"unexpected teacher_profile: {x.get('teacher_profile')!r}")`。
- `validate_teacher_manifest`，第 294 行：`RuntimeError(f"unexpected teacher_git_sha: {x.get('teacher_git_sha')!r}")`。
- `validate_teacher_manifest`，第 301 行：`RuntimeError('Teacher v4 directional semantic gate not frozen PASS')`。
- `validate_teacher_manifest`，第 306 行：`RuntimeError('Teacher v4 directional closed-loop gate not frozen PASS')`。
- `validate_wave1_plan`，第 236 行：`RuntimeError(f"unexpected Wave1 plan version: {payload.get('plan_version')!r}")`。
- `validate_wave1_plan`，第 243 行：`RuntimeError(f"Wave1 plan must contain 1000 rows, got {(len(plan) if isinstance(plan, list) else '<invalid>')}")`。
- `validate_wave1_plan`，第 254 行：`RuntimeError('Wave1 contains invalid extension_seed')`。
- `validate_wave1_plan`，第 257 行：`RuntimeError('Wave1 contains duplicate extension_seed')`。
- `validate_wave1_plan`，第 260 行：`RuntimeError(f'Wave1 seed namespace mismatch: {min(seeds)}..{max(seeds)}')`。
- `validate_wave1_plan`，第 268 行：`RuntimeError('Wave1 missing plan_canonical_sha256')`。
- `validate_wave1_plan`，第 277 行：`RuntimeError(f'Wave1 canonical hash mismatch embedded={embedded_sha} actual={actual}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 698 行：`ap.add_argument('--registry', required=True)`。
- 第 699 行：`ap.add_argument('--prior-d1-plan', required=True)`。
- 第 700 行：`ap.add_argument('--prior-wave1-plan', required=True)`。
- 第 701 行：`ap.add_argument('--teacher-manifest-v4', required=True)`。
- 第 702 行：`ap.add_argument('--semantic-report-v4', required=True)`。
- 第 703 行：`ap.add_argument('--eligibility-report-v4', required=True)`。
- 第 704 行：`ap.add_argument('--output-dir', required=True)`。
- 第 706 行：`ap.add_argument('--dry-run', action='store_true')`。
- 第 707 行：`ap.add_argument('--allow-uncommitted-code', action='store_true')`。

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

### `challenge/dataset/build_d2_wave2_plan.py`

来源 SHA256：`a34b32b8142f97bd9cb66db84b0c8c136d3fb61b832331f50395197879b723b3`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 698 | `'--registry'` | `required=True` |
| 699 | `'--prior-d1-plan'` | `required=True` |
| 700 | `'--prior-wave1-plan'` | `required=True` |
| 701 | `'--teacher-manifest-v4'` | `required=True` |
| 702 | `'--semantic-report-v4'` | `required=True` |
| 703 | `'--eligibility-report-v4'` | `required=True` |
| 704 | `'--output-dir'` | `required=True` |
| 706 | `'--dry-run'` | `action='store_true'` |
| 707 | `'--allow-uncommitted-code'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_registry` / 208 | `not rows or not required.issubset(rows[0])` | `raise RuntimeError(f'registry schema mismatch: {sorted(rows[0] if rows else [])}')` |
| `load_plan_seed_values` / 220 | `not isinstance(plan, list)` | `raise RuntimeError(f'plan[] missing: {path}')` |
| `validate_wave1_plan` / 236 | `payload.get('plan_version') != EXPECTED_WAVE1_PLAN_VERSION` | `raise RuntimeError(f"unexpected Wave1 plan version: {payload.get('plan_version')!r}")` |
| `validate_wave1_plan` / 243 | `not isinstance(plan, list) or len(plan) != 1000` | `raise RuntimeError(f"Wave1 plan must contain 1000 rows, got {(len(plan) if isinstance(plan, list) else '<invalid>')}")` |
| `validate_wave1_plan` / 254 | `any((type(seed) is not int for seed in seeds))` | `raise RuntimeError('Wave1 contains invalid extension_seed')` |
| `validate_wave1_plan` / 257 | `len(seeds) != len(set(seeds))` | `raise RuntimeError('Wave1 contains duplicate extension_seed')` |
| `validate_wave1_plan` / 260 | `min(seeds) != 2000000 or max(seeds) != 2000999` | `raise RuntimeError(f'Wave1 seed namespace mismatch: {min(seeds)}..{max(seeds)}')` |
| `validate_wave1_plan` / 268 | `not isinstance(embedded_sha, str)` | `raise RuntimeError('Wave1 missing plan_canonical_sha256')` |
| `validate_wave1_plan` / 277 | `actual != embedded_sha` | `raise RuntimeError(f'Wave1 canonical hash mismatch embedded={embedded_sha} actual={actual}')` |
| `validate_teacher_manifest` / 289 | `x.get('teacher_profile') != EXPECTED_TEACHER_PROFILE` | `raise RuntimeError(f"unexpected teacher_profile: {x.get('teacher_profile')!r}")` |
| `validate_teacher_manifest` / 294 | `x.get('teacher_git_sha') != EXPECTED_TEACHER_GIT_SHA` | `raise RuntimeError(f"unexpected teacher_git_sha: {x.get('teacher_git_sha')!r}")` |
| `validate_teacher_manifest` / 301 | `verification.get('directional_semantic_gate') != '8/8 PASS'` | `raise RuntimeError('Teacher v4 directional semantic gate not frozen PASS')` |
| `validate_teacher_manifest` / 306 | `verification.get('directional_closed_loop_gate') != '8/8 SUCCEEDED'` | `raise RuntimeError('Teacher v4 directional closed-loop gate not frozen PASS')` |
| `validate_semantic_report` / 323 | `except Exception` | `raise RuntimeError('semantic governance report schema mismatch') from exc` |
| `validate_semantic_report` / 328 | `(d1, d2, total) != (8, 181, 189)` | `raise RuntimeError(f'unexpected semantic quarantine counts: D1={d1} D2={d2} TOTAL={total}')` |
| `validate_eligibility_report` / 346 | `except Exception` | `raise RuntimeError('training eligibility report schema mismatch') from exc` |
| `validate_eligibility_report` / 351 | `(d1, d2, hn, cumulative) != (122, 953, 64, 1075)` | `raise RuntimeError(f'unexpected eligibility counts: D1={d1} D2={d2} HN={hn} cumulative={cumulative}')` |
| `candidate_pool` / 492 | `本地无直接if；检查上下文` | `raise RuntimeError(f'unknown quota bucket {bucket}')` |
| `build_plan` / 507 | `collision` | `raise RuntimeError(f'Wave2 reserved seed namespace overlaps prior acquisition: {sorted(collision)[:20]}')` |
| `build_plan` / 529 | `capacity < target` | `raise RuntimeError(f'raw capacity insufficient for {bucket}: target={target} capacity={capacity} scenarios={len(pool)}')` |
| `build_plan` / 650 | `len(plan) != PLANNED_RUNS` | `raise RuntimeError(f'planned run count mismatch: {len(plan)}')` |
| `build_plan` / 658 | `len(seeds) != len(set(seeds))` | `raise RuntimeError('duplicate extension_seed')` |
| `build_plan` / 661 | `len(ids) != len(set(ids))` | `raise RuntimeError('duplicate extension_id')` |
| `build_plan` / 664 | `set(seeds) & prior_seeds` | `raise RuntimeError('Wave2 seed overlaps prior acquisition')` |
| `build_plan` / 667 | `seeds != list(range(SEED_START, SEED_START + PLANNED_RUNS))` | `raise RuntimeError(f'Wave2 seeds must exactly occupy reserved namespace {SEED_START}..{SEED_START + PLANNED_RUNS - 1}')` |
| `build_plan` / 687 | `dict(recollection_counts) != expected_recollection` | `raise RuntimeError(f'directional recollection must be exactly balanced 30/scenario: {dict(sorted(recollection_counts.items()))}')` |
| `build_plan.allocate` / 560 | `not pool` | `raise RuntimeError(f'empty candidate pool for {bucket}')` |
| `build_plan.allocate` / 582 | `cursor >= len(pool) AND stalled_rounds > len(pool) + 2` | `raise RuntimeError(f'cannot satisfy quota {bucket}: target={target} made={made}')` |
| `build_plan.allocate` / 598 | `next_seed >= SEED_START + PLANNED_RUNS` | `raise RuntimeError('Wave2 seed namespace exhausted')` |
| `build_plan.allocate` / 601 | `next_seed in prior_seeds` | `raise RuntimeError(f'unexpected prior seed collision: {next_seed}')` |
| `main` / 738 | `not path.is_file()` | `raise RuntimeError(f'required file missing: {path}')` |
| `main` / 743 | `registry_sha != EXPECTED_REGISTRY_SHA256` | `raise RuntimeError(f'registry SHA mismatch expected={EXPECTED_REGISTRY_SHA256} actual={registry_sha}')` |
| `main` / 752 | `prior_d1_sha != EXPECTED_PRIOR_D1_PLAN_SHA256` | `raise RuntimeError(f'prior D1 plan SHA mismatch expected={EXPECTED_PRIOR_D1_PLAN_SHA256} actual={prior_d1_sha}')` |
| `main` / 803 | `any((row['source_bucket'] == 'UNSEEN' for row in train_positive))` | `raise RuntimeError('UNSEEN appears inside TRAIN_POSITIVE registry rows')` |
| `main` / 811 | `any(('RESERVED_TEST' in row.get('policy_class', '') for row in train_positive))` | `raise RuntimeError('reserved Test row leaked into TRAIN_POSITIVE')` |
| `main` / 822 | `missing_files` | `raise RuntimeError(f'scenario files missing: {missing_files[:20]}')` |
| `main` / 836 | `missing_directional` | `raise RuntimeError(f'directional recollection sources missing from TRAIN_POSITIVE registry: {sorted(missing_directional)}')` |
| `main` / 850 | `prior_d1_seeds & wave1_seeds` | `raise RuntimeError('historical D1/Wave1 seed collision detected')` |
| `main` / 887 | `normalized_bucket_counts != QUOTAS` | `raise RuntimeError(f'quota mismatch expected={QUOTAS} actual={normalized_bucket_counts}')` |

# collect_d2_expansion：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/collect_d2_expansion.py](../../../challenge/dataset/collect_d2_expansion.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

B1 D2 expansion collector.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `load_json`

源码位置：[challenge/dataset/collect_d2_expansion.py 第 24 行](../../../challenge/dataset/collect_d2_expansion.py#L24)。类型：`FunctionDef`。

```python
load_json(path: Path) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `health`

源码位置：[challenge/dataset/collect_d2_expansion.py 第 28 行](../../../challenge/dataset/collect_d2_expansion.py#L28)。类型：`FunctionDef`。

```python
health(url: str, pinned: dict) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `git_output`

源码位置：[challenge/dataset/collect_d2_expansion.py 第 48 行](../../../challenge/dataset/collect_d2_expansion.py#L48)。类型：`FunctionDef`。

```python
git_output(repo: Path, *args: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_teacher_repo`

源码位置：[challenge/dataset/collect_d2_expansion.py 第 63 行](../../../challenge/dataset/collect_d2_expansion.py#L63)。类型：`FunctionDef`。

```python
verify_teacher_repo(teacher_repo: Path) -> dict
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_case`

源码位置：[challenge/dataset/collect_d2_expansion.py 第 92 行](../../../challenge/dataset/collect_d2_expansion.py#L92)。类型：`FunctionDef`。

```python
run_case(teacher_repo, challenge_repo, item, service, logs, images) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `collect`

源码位置：[challenge/dataset/collect_d2_expansion.py 第 116 行](../../../challenge/dataset/collect_d2_expansion.py#L116)。类型：`FunctionDef`。

```python
collect(repo, logs, dataset) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/collect_d2_expansion.py 第 136 行](../../../challenge/dataset/collect_d2_expansion.py#L136)。类型：`FunctionDef`。

```python
main() -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `load_json` 调用：`json.loads`, `path.read_text`.
- `health` 调用：`RuntimeError`, `data.get`, `json.loads`, `r.read`, `url.rstrip`, `urllib.request.urlopen`.
- `git_output` 调用：`' '.join`, `RuntimeError`, `result.stderr.strip`, `result.stdout.strip`, `str`, `subprocess.run`.
- `verify_teacher_repo` 调用：`RuntimeError`, `git_output`, `str`, `teacher_repo.is_dir`, `teacher_repo.resolve`.
- `run_case` 调用：`images.relative_to`, `item['scenario_path'].startswith`, `print`, `str`, `subprocess.run`.
- `collect` 调用：`RuntimeError`, `logs.glob`, `sorted`, `str`, `subprocess.run`.
- `main` 调用：`(out / 'provenance_manifest.json').write_text`, `(repo / teacher_repo).resolve`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `any`, `argparse.ArgumentParser`, `collect`, `d.mkdir`, `git_output`, `health`, `int`, `json.dumps`, `len`, `load_json`, `out.is_absolute`, `out.resolve`, `p.add_argument`, `p.parse_args`, `path.is_file`, `pinned.get`, `print`, `required_pin.items`, `run_case`, `runner_failures.append`, `set`, `str`, `teacher_repo.is_absolute`, `verify_teacher_repo`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `collect`，第 133 行：`RuntimeError('collector failed')`。
- `git_output`，第 57 行：`RuntimeError(f"git {' '.join(args)} failed for {repo}: {result.stderr.strip()}")`。
- `health`，第 33 行：`RuntimeError('Teacher service not ready')`。
- `health`，第 35 行：`RuntimeError('Teacher service is not production_ready')`。
- `health`，第 37 行：`RuntimeError(f"Teacher model mismatch: {data.get('model_id')} != {pinned['model_id']}")`。
- `health`，第 41 行：`RuntimeError(f"Teacher mode mismatch: {data.get('qwen_mode')} != {pinned['qwen_mode']}")`。
- `main`，第 169 行：`RuntimeError('duplicate seeds')`。
- `main`，第 180 行：`RuntimeError('missing scenario ' + scenario_path)`。
- `main`，第 210 行：`RuntimeError(f'Teacher pin mismatch for {key}: {pinned.get(key)!r} != {expected!r}')`。
- `verify_teacher_repo`，第 65 行：`RuntimeError(f'Teacher repo does not exist: {teacher_repo}')`。
- `verify_teacher_repo`，第 69 行：`RuntimeError(f'Teacher HEAD mismatch: {head} != {EXPECTED_TEACHER_GIT_SHA}')`。
- `verify_teacher_repo`，第 81 行：`RuntimeError('Teacher tracked worktree is dirty:\n' + tracked_status)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 138 行：`p.add_argument('--plan', default='artifacts/b1_d2_expansion_plan_v1/d2_expansion_plan_wave1.json')`。
- 第 142 行：`p.add_argument('--max-runs', type=int)`。
- 第 143 行：`p.add_argument('--dry-run', action='store_true')`。
- 第 144 行：`p.add_argument('--qwen-service-url', default='http://127.0.0.1:18003')`。
- 第 145 行：`p.add_argument('--teacher-repo-root', default=DEFAULT_TEACHER_REPO_ROOT, help='Frozen verified main worktree used to execute Teacher scenarios')`。
- 第 150 行：`p.add_argument('--output-root', default='artifacts/b1_d2_expansion_wave1', help='Challenge-repo output directory for logs, images, dataset, and provenance')`。

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

### `challenge/dataset/collect_d2_expansion.py`

来源 SHA256：`37fb00511f1517b66bcc518d1e08ad37e689954824666e923175062f02b8d956`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 138 | `'--plan'` | `default='artifacts/b1_d2_expansion_plan_v1/d2_expansion_plan_wave1.json'` |
| 142 | `'--max-runs'` | `type=int` |
| 143 | `'--dry-run'` | `action='store_true'` |
| 144 | `'--qwen-service-url'` | `default='http://127.0.0.1:18003'` |
| 145 | `'--teacher-repo-root'` | `default=DEFAULT_TEACHER_REPO_ROOT; help='Frozen verified main worktree used to execute Teacher scenarios'` |
| 150 | `'--output-root'` | `default='artifacts/b1_d2_expansion_wave1'; help='Challenge-repo output directory for logs, images, dataset, and provenance'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `health` / 33 | `data.get('status') != 'READY'` | `raise RuntimeError('Teacher service not ready')` |
| `health` / 35 | `data.get('production_ready') is not True` | `raise RuntimeError('Teacher service is not production_ready')` |
| `health` / 37 | `data.get('model_id') != pinned['model_id']` | `raise RuntimeError(f"Teacher model mismatch: {data.get('model_id')} != {pinned['model_id']}")` |
| `health` / 41 | `data.get('qwen_mode') != pinned['qwen_mode']` | `raise RuntimeError(f"Teacher mode mismatch: {data.get('qwen_mode')} != {pinned['qwen_mode']}")` |
| `git_output` / 57 | `result.returncode != 0` | `raise RuntimeError(f"git {' '.join(args)} failed for {repo}: {result.stderr.strip()}")` |
| `verify_teacher_repo` / 65 | `not teacher_repo.is_dir()` | `raise RuntimeError(f'Teacher repo does not exist: {teacher_repo}')` |
| `verify_teacher_repo` / 69 | `head != EXPECTED_TEACHER_GIT_SHA` | `raise RuntimeError(f'Teacher HEAD mismatch: {head} != {EXPECTED_TEACHER_GIT_SHA}')` |
| `verify_teacher_repo` / 81 | `tracked_status` | `raise RuntimeError('Teacher tracked worktree is dirty:\n' + tracked_status)` |
| `collect` / 133 | `subprocess.run(cmd, cwd=repo, check=False).returncode` | `raise RuntimeError('collector failed')` |
| `main` / 169 | `len(seeds) != len(set(seeds))` | `raise RuntimeError('duplicate seeds')` |
| `main` / 180 | `not any((path.is_file() for path in candidate_paths))` | `raise RuntimeError('missing scenario ' + scenario_path)` |
| `main` / 210 | `pinned.get(key) != expected` | `raise RuntimeError(f'Teacher pin mismatch for {key}: {pinned.get(key)!r} != {expected!r}')` |

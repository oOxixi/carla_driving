# collect_pinned_mini_smoke：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/collect_pinned_mini_smoke.py](../../../challenge/dataset/collect_pinned_mini_smoke.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

collect_pinned_mini_smoke

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `count_jsonl`

源码位置：[challenge/dataset/collect_pinned_mini_smoke.py 第 28 行](../../../challenge/dataset/collect_pinned_mini_smoke.py#L28)。类型：`FunctionDef`。

```python
count_jsonl(path: Path) -> int
```

`count_jsonl` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `health`

源码位置：[challenge/dataset/collect_pinned_mini_smoke.py 第 34 行](../../../challenge/dataset/collect_pinned_mini_smoke.py#L34)。类型：`FunctionDef`。

```python
health(url: str) -> dict[str, Any]
```

`health` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `collect`

源码位置：[challenge/dataset/collect_pinned_mini_smoke.py 第 52 行](../../../challenge/dataset/collect_pinned_mini_smoke.py#L52)。类型：`FunctionDef`。

```python
collect(repo: Path, logs: Path, dataset: Path) -> tuple[int, int]
```

`collect` 执行采集或从运行日志汇总样本/证据；运行成功、结构有效、闭环成功和训练资格是分开的判断，失败记录不得静默丢弃。

### `main`

源码位置：[challenge/dataset/collect_pinned_mini_smoke.py 第 83 行](../../../challenge/dataset/collect_pinned_mini_smoke.py#L83)。类型：`FunctionDef`。

```python
main() -> int
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `count_jsonl` 调用：`path.is_file`, `path.read_text`, `path.read_text(encoding='utf-8').splitlines`, `sum`, `x.strip`.
- `health` 调用：`RuntimeError`, `data.get`, `json.loads`, `print`, `r.read`, `r.read().decode`, `str`, `url.rstrip`, `urllib.request.urlopen`.
- `collect` 调用：`RuntimeError`, `count_jsonl`, `logs.glob`, `sorted`, `str`, `subprocess.run`.
- `main` 调用：`(root / 'pinned_mini_smoke_summary.json').write_text`, `(root / 'pinned_smoke_provenance.json').write_text`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `argparse.ArgumentParser`, `collect`, `d.mkdir`, `data.get`, `enumerate`, `expected_identity.items`, `failed.append`, `health`, `json.dumps`, `json.loads`, `len`, `p.add_argument`, `p.parse_args`, `pinned_manifest.is_file`, `pinned_manifest.read_text`, `print`, `provenance.get`, `scenario.is_file`, `scenario.read_text`, `str`, `subprocess.run`, `valid.is_file`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `collect`，第 79 行：`RuntimeError('collector.py failed')`。
- `health`，第 42 行：`RuntimeError('Teacher status is not READY')`。
- `health`，第 44 行：`RuntimeError('Teacher not production_ready')`。
- `health`，第 46 行：`RuntimeError('Unexpected Teacher model')`。
- `health`，第 48 行：`RuntimeError('Unexpected qwen_mode')`。
- `main`，第 127 行：`RuntimeError('Configured --runner-python cannot import CARLA Python API')`。
- `main`，第 133 行：`RuntimeError('challenge/teacher_baseline_manifest.json not found')`。
- `main`，第 149 行：`RuntimeError('Pinned Teacher identity mismatch: ' + json.dumps(mismatch, ensure_ascii=False))`。
- `main`，第 161 行：`RuntimeError(f'Missing scenario: {rel}')`。
- `main`，第 226 行：`RuntimeError('validate_dataset.py failed')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 85 行：`p.add_argument('--qwen-service-url', default='http://127.0.0.1:18004')`。
- 第 86 行：`p.add_argument('--runner-python', default='/home/dcase_task2/miniconda3/envs/voice/bin/python', help='Python interpreter used for integration.carla_runner')`。
- 第 91 行：`p.add_argument('--dry-run', action='store_true')`。

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

### `challenge/dataset/collect_pinned_mini_smoke.py`

来源 SHA256：`c182aa258be64950871c2c69a3b90efcc5925d4202448ac3009688bfc323f506`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 85 | `'--qwen-service-url'` | `default='http://127.0.0.1:18004'` |
| 86 | `'--runner-python'` | `default='/home/dcase_task2/miniconda3/envs/voice/bin/python'; help='Python interpreter used for integration.carla_runner'` |
| 91 | `'--dry-run'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `health` / 42 | `data.get('status') != 'READY'` | `raise RuntimeError('Teacher status is not READY')` |
| `health` / 44 | `data.get('production_ready') is not True` | `raise RuntimeError('Teacher not production_ready')` |
| `health` / 46 | `data.get('model_id') != 'Qwen/Qwen3.5-2B'` | `raise RuntimeError('Unexpected Teacher model')` |
| `health` / 48 | `data.get('qwen_mode') != 'planner_v2'` | `raise RuntimeError('Unexpected qwen_mode')` |
| `collect` / 79 | `rc != 0` | `raise RuntimeError('collector.py failed')` |
| `main` / 127 | `runner_check.returncode != 0` | `raise RuntimeError('Configured --runner-python cannot import CARLA Python API')` |
| `main` / 133 | `not pinned_manifest.is_file()` | `raise RuntimeError('challenge/teacher_baseline_manifest.json not found')` |
| `main` / 149 | `mismatch` | `raise RuntimeError('Pinned Teacher identity mismatch: ' + json.dumps(mismatch, ensure_ascii=False))` |
| `main` / 161 | `not scenario.is_file()` | `raise RuntimeError(f'Missing scenario: {rel}')` |
| `main` / 226 | `valid.is_file() AND rc != 0` | `raise RuntimeError('validate_dataset.py failed')` |

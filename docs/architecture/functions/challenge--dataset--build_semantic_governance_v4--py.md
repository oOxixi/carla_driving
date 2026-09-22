# build_semantic_governance_v4：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_semantic_governance_v4.py](../../../challenge/dataset/build_semantic_governance_v4.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_semantic_governance_v4

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 47 行](../../../challenge/dataset/build_semantic_governance_v4.py#L47)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `canonical_json_sha256`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 55 行](../../../challenge/dataset/build_semantic_governance_v4.py#L55)。类型：`FunctionDef`。

```python
canonical_json_sha256(obj: dict) -> str
```

`canonical_json_sha256` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `load_jsonl`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 65 行](../../../challenge/dataset/build_semantic_governance_v4.py#L65)。类型：`FunctionDef`。

```python
load_jsonl(path: Path) -> list[dict]
```

`load_jsonl` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `scenario_key`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 77 行](../../../challenge/dataset/build_semantic_governance_v4.py#L77)。类型：`FunctionDef`。

```python
scenario_key(row: dict) -> str | None
```

`scenario_key` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `behaviors`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 92 行](../../../challenge/dataset/build_semantic_governance_v4.py#L92)。类型：`FunctionDef`。

```python
behaviors(row: dict) -> list[str]
```

`behaviors` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `identity`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 101 行](../../../challenge/dataset/build_semantic_governance_v4.py#L101)。类型：`FunctionDef`。

```python
identity(row: dict) -> dict
```

`identity` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `classify`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 114 行](../../../challenge/dataset/build_semantic_governance_v4.py#L114)。类型：`FunctionDef`。

```python
classify(row: dict) -> dict | None
```

`classify` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `dump_jsonl`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 211 行](../../../challenge/dataset/build_semantic_governance_v4.py#L211)。类型：`FunctionDef`。

```python
dump_jsonl(path: Path, rows: list[dict]) -> None
```

`dump_jsonl` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `main`

源码位置：[challenge/dataset/build_semantic_governance_v4.py 第 220 行](../../../challenge/dataset/build_semantic_governance_v4.py#L220)。类型：`FunctionDef`。

```python
main() -> None
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `canonical_json_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(payload).hexdigest`, `json.dumps`, `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode`.
- `load_jsonl` 调用：`enumerate`, `json.loads`, `line.strip`, `path.open`, `rows.append`.
- `scenario_key` 调用：`Path`, `meta.get`, `row.get`, `str`.
- `behaviors` 调用：`isinstance`, `plan.get`, `row.get`, `step.get`, `str`.
- `identity` 调用：`meta.get`, `row.get`.
- `classify` 调用：`(row.get('closed_loop_quality') or {}).get`, `(row.get('model_request') or {}).get`, `(row.get('quality') or {}).get`, `behaviors`, `hint.get`, `identity`, `meta.get`, `row.get`, `scenario_key`.
- `dump_jsonl` 调用：`f.write`, `json.dumps`, `path.open`.
- `main` 调用：`''.join`, `(out / 'directional_quarantine_ids.txt').write_text`, `(out / f'{label.lower()}_directional_quarantine_ids.txt').write_text`, `(out / f'{label.lower()}_unaffected_candidate_ids.txt').write_text`, `AssertionError`, `Counter`, `FileNotFoundError`, `all_quarantine.extend`, `all_unaffected_ids.extend`, `argparse.ArgumentParser`, `args.d1_jsonl.resolve`, `args.d2_jsonl.resolve`, `args.output_root.resolve`, `canonical_json_sha256`, `classify`, `datasets.items`, `dict`, `dump_jsonl`, `findings.append`, `json.dumps`, `label.lower`, `len`, `load_jsonl`, `out.mkdir`, `parser.add_argument`, `parser.parse_args`, `path.is_file`, `print`, `report.items`, `report_path.write_text`, `rows[0].get`, `scenario_counts.items`, `set`, `sha256_file`, `sorted`, `str`, `subprocess.check_output`, `subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip`, `unaffected_ids.append`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 281 行：`FileNotFoundError(path)`。
- `main`，第 319 行：`AssertionError(f'{label}: expected {EXPECTED[label]} confirmed directional contaminations, got {len(contaminated)}')`。
- `main`，第 325 行：`AssertionError(f'{label}: historical directional rows unexpectedly already correct: {len(correct_directional)}')`。
- `main`，第 331 行：`AssertionError(f'{label}: unexpected directional states found: {len(unexpected)}')`。
- `main`，第 342 行：`AssertionError(f'{label}: duplicate quarantine sample_id')`。
- `main`，第 402 行：`AssertionError(f'expected 189 total quarantine rows, got {len(all_ids)}')`。
- `main`，第 407 行：`AssertionError('sample_id overlap exists across D1/D2 quarantine')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 226 行：`parser.add_argument('--d1-jsonl', type=Path, required=True, help='Frozen D1 valid JSONL')`。
- 第 232 行：`parser.add_argument('--d2-jsonl', type=Path, required=True, help='Frozen D2 Wave1 valid JSONL')`。
- 第 238 行：`parser.add_argument('--output-root', type=Path, required=True, help='Output directory for governance artifacts')`。

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

### `challenge/dataset/build_semantic_governance_v4.py`

来源 SHA256：`688b3405225caec859cc378ff16a40241efcc378236aaf608ddc3ce19b454285`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 226 | `'--d1-jsonl'` | `type=Path; required=True; help='Frozen D1 valid JSONL'` |
| 232 | `'--d2-jsonl'` | `type=Path; required=True; help='Frozen D2 Wave1 valid JSONL'` |
| 238 | `'--output-root'` | `type=Path; required=True; help='Output directory for governance artifacts'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 281 | `not path.is_file()` | `raise FileNotFoundError(path)` |
| `main` / 319 | `len(contaminated) != EXPECTED[label]` | `raise AssertionError(f'{label}: expected {EXPECTED[label]} confirmed directional contaminations, got {len(contaminated)}')` |
| `main` / 325 | `correct_directional` | `raise AssertionError(f'{label}: historical directional rows unexpectedly already correct: {len(correct_directional)}')` |
| `main` / 331 | `unexpected` | `raise AssertionError(f'{label}: unexpected directional states found: {len(unexpected)}')` |
| `main` / 342 | `len(ids) != len(set(ids))` | `raise AssertionError(f'{label}: duplicate quarantine sample_id')` |
| `main` / 402 | `len(all_ids) != 189` | `raise AssertionError(f'expected 189 total quarantine rows, got {len(all_ids)}')` |
| `main` / 407 | `len(all_ids) != len(set(all_ids))` | `raise AssertionError('sample_id overlap exists across D1/D2 quarantine')` |

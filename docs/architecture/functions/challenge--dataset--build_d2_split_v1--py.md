# build_d2_split_v1：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d2_split_v1.py](../../../challenge/dataset/build_d2_split_v1.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d2_split_v1

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `load_jsonl`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 27 行](../../../challenge/dataset/build_d2_split_v1.py#L27)。类型：`FunctionDef`。

```python
load_jsonl(path: Path) -> list[dict]
```

`load_jsonl` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `read_ids`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 36 行](../../../challenge/dataset/build_d2_split_v1.py#L36)。类型：`FunctionDef`。

```python
read_ids(path: Path) -> set[str]
```

`read_ids` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `sha256_file`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 44 行](../../../challenge/dataset/build_d2_split_v1.py#L44)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `canonical_sha`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 52 行](../../../challenge/dataset/build_d2_split_v1.py#L52)。类型：`FunctionDef`。

```python
canonical_sha(obj: object) -> str
```

`canonical_sha` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `stable_hash`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 62 行](../../../challenge/dataset/build_d2_split_v1.py#L62)。类型：`FunctionDef`。

```python
stable_hash(text: str) -> str
```

`stable_hash` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `sample_role`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 66 行](../../../challenge/dataset/build_d2_split_v1.py#L66)。类型：`FunctionDef`。

```python
sample_role(row: dict) -> str
```

`sample_role` 按当前策略把场景或样本映射到治理类别、配额或状态；分类结果会影响训练资格和切分，修改规则需版本化并重建报告。

### `group_key`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 73 行](../../../challenge/dataset/build_d2_split_v1.py#L73)。类型：`FunctionDef`。

```python
group_key(row: dict) -> str
```

`group_key` 参与分组、候选或确定性切分与分配；必须保持同组不跨split、seed可复现并记录未满足配额，不能靠重跑挑选有利结果。

### `scenario_family`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 106 行](../../../challenge/dataset/build_d2_split_v1.py#L106)。类型：`FunctionDef`。

```python
scenario_family(row: dict) -> str
```

`scenario_family` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `write_jsonl`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 111 行](../../../challenge/dataset/build_d2_split_v1.py#L111)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: list[dict]) -> None
```

`write_jsonl` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `choose_split`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 124 行](../../../challenge/dataset/build_d2_split_v1.py#L124)。类型：`FunctionDef`。

```python
choose_split(group_rows: list[dict], current_total: Counter, current_roles: dict[str, Counter], targets_total: dict[str, float], targets_roles: dict[str, dict[str, float]]) -> str
```

Deterministic group-aware allocation.

Primary objective:
    minimize GLOBAL split-size error after placing the group.

Secondary objective:
    minimize training-role imbalance.

The previous implementation compared only the candidate split's
own normalized error. That systematically overfilled the smaller
VAL / RESERVED_TEST_CANDIDATE targets.

### `main`

源码位置：[challenge/dataset/build_d2_split_v1.py 第 227 行](../../../challenge/dataset/build_d2_split_v1.py#L227)。类型：`FunctionDef`。

```python
main() -> None
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `load_jsonl` 调用：`json.loads`, `line.strip`, `out.append`, `path.open`.
- `read_ids` 调用：`path.read_text`, `path.read_text(encoding='utf-8').splitlines`, `x.strip`.
- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `canonical_sha` 调用：`hashlib.sha256`, `hashlib.sha256(payload).hexdigest`, `json.dumps`, `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode`.
- `stable_hash` 调用：`hashlib.sha256`, `hashlib.sha256(text.encode('utf-8')).hexdigest`, `text.encode`.
- `sample_role` 调用：`(row.get('quality') or {}).get`, `row.get`, `str`.
- `group_key` 调用：`json.dumps`, `meta.get`, `row.get`, `str`.
- `scenario_family` 调用：`meta.get`, `row.get`, `str`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`.
- `choose_split` 调用：`Counter`, `g_roles.get`, `len`, `max`, `sample_role`, `sum`.
- `main` 调用：`''.join`, `(out / filename.replace('.jsonl', '_sample_ids.txt')).write_text`, `(row.get('metadata') or {}).get`, `Counter`, `Counter((x['scenario_family'] for x in rows)).items`, `Counter((x['source'] for x in rows)).items`, `Path`, `RATIOS.items`, `abs`, `actual_ratios.items`, `all`, `argparse.ArgumentParser`, `args.d1_jsonl.resolve`, `args.historical_eligibility_root.resolve`, `args.output_root.resolve`, `args.wave1_jsonl.resolve`, `args.wave2_governance_root.resolve`, `args.wave2_jsonl.resolve`, `assignments.append`, `canonical_sha`, `choose_split`, `clean_row.pop`, `defaultdict`, `dict`, `enumerate`, `filename.replace`, `group_key`, `groups.items`, `groups[group_key(row)].append`, `groups_by_split[a].isdisjoint`, `ids_by_split[a].isdisjoint`, `json.dumps`, `len`, `list`, `load_jsonl`, `manifest_path.write_text`, `normalized.append`, `out.mkdir`, `p.stat`, `parser.add_argument`, `parser.parse_args`, `print`, `ratio_deviation.items`, `ratio_deviation.values`, `read_ids`, `report_path.write_text`, `round`, `row.get`, `scenario_family`, `set`, `sha256_file`, `sorted`, `split_rows.items`, `split_rows.values`, `split_rows[split].append`, `stable_hash`, `str`, `subprocess.check_output`, `subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip`, `sum`, `write_jsonl`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 230 行：`parser.add_argument('--d1-jsonl', type=Path, required=True)`。
- 第 231 行：`parser.add_argument('--wave1-jsonl', type=Path, required=True)`。
- 第 233 行：`parser.add_argument('--wave2-jsonl', type=Path, default=Path('artifacts/b1_d2_wave2_2000_teacher_v4/dataset/d2_valid.jsonl'))`。
- 第 242 行：`parser.add_argument('--historical-eligibility-root', type=Path, default=Path('artifacts/b1_training_eligibility_v4'))`。
- 第 248 行：`parser.add_argument('--wave2-governance-root', type=Path, default=Path('artifacts/b1_d2_cumulative_governance_v5'))`。
- 第 254 行：`parser.add_argument('--output-root', type=Path, default=Path('artifacts/b1_d2_split_v1'))`。

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

### `challenge/dataset/build_d2_split_v1.py`

来源 SHA256：`4d10773fe145a9de997772441bc521c9d58adf80b6ab29fe6293542483e1b3dc`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 230 | `'--d1-jsonl'` | `type=Path; required=True` |
| 231 | `'--wave1-jsonl'` | `type=Path; required=True` |
| 233 | `'--wave2-jsonl'` | `type=Path; default=Path('artifacts/b1_d2_wave2_2000_teacher_v4/dataset/d2_valid.jsonl')` |
| 242 | `'--historical-eligibility-root'` | `type=Path; default=Path('artifacts/b1_training_eligibility_v4')` |
| 248 | `'--wave2-governance-root'` | `type=Path; default=Path('artifacts/b1_d2_cumulative_governance_v5')` |
| 254 | `'--output-root'` | `type=Path; default=Path('artifacts/b1_d2_split_v1')` |

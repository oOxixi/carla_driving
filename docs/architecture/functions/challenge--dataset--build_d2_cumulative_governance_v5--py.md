# build_d2_cumulative_governance_v5：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d2_cumulative_governance_v5.py](../../../challenge/dataset/build_d2_cumulative_governance_v5.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d2_cumulative_governance_v5

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_d2_cumulative_governance_v5.py 第 28 行](../../../challenge/dataset/build_d2_cumulative_governance_v5.py#L28)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `canonical_sha256`

源码位置：[challenge/dataset/build_d2_cumulative_governance_v5.py 第 36 行](../../../challenge/dataset/build_d2_cumulative_governance_v5.py#L36)。类型：`FunctionDef`。

```python
canonical_sha256(obj: object) -> str
```

`canonical_sha256` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `load_jsonl`

源码位置：[challenge/dataset/build_d2_cumulative_governance_v5.py 第 46 行](../../../challenge/dataset/build_d2_cumulative_governance_v5.py#L46)。类型：`FunctionDef`。

```python
load_jsonl(path: Path) -> list[dict]
```

`load_jsonl` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `write_ids`

源码位置：[challenge/dataset/build_d2_cumulative_governance_v5.py 第 55 行](../../../challenge/dataset/build_d2_cumulative_governance_v5.py#L55)。类型：`FunctionDef`。

```python
write_ids(path: Path, ids: set[str]) -> None
```

`write_ids` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `behaviors`

源码位置：[challenge/dataset/build_d2_cumulative_governance_v5.py 第 62 行](../../../challenge/dataset/build_d2_cumulative_governance_v5.py#L62)。类型：`FunctionDef`。

```python
behaviors(row: dict) -> list[str]
```

`behaviors` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `main`

源码位置：[challenge/dataset/build_d2_cumulative_governance_v5.py 第 70 行](../../../challenge/dataset/build_d2_cumulative_governance_v5.py#L70)。类型：`FunctionDef`。

```python
main() -> None
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `canonical_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(data).hexdigest`, `json.dumps`, `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode`.
- `load_jsonl` 调用：`json.loads`, `line.strip`, `path.open`, `rows.append`.
- `write_ids` 调用：`''.join`, `path.write_text`, `sorted`.
- `behaviors` 调用：`(row.get('teacher_plan') or {}).get`, `isinstance`, `row.get`, `step.get`, `str`.
- `main` 调用：`(row.get('metadata') or {}).get`, `(row.get('model_request') or {}).get`, `(row.get('quality') or {}).get`, `Counter`, `Path`, `all`, `argparse.ArgumentParser`, `args.output_root.resolve`, `args.previous_eligibility_root.resolve`, `args.wave2_freeze.resolve`, `args.wave2_jsonl.resolve`, `behaviors`, `canonical_sha256`, `dict`, `directional_counts.items`, `directional_unexpected.append`, `freeze_path.is_file`, `freeze_path.read_text`, `hint.get`, `json.dumps`, `json.loads`, `len`, `load_jsonl`, `meta.get`, `out.mkdir`, `parser.add_argument`, `parser.parse_args`, `positive_ids.isdisjoint`, `prev_report_path.is_file`, `prev_report_path.read_text`, `print`, `report_path.write_text`, `row.get`, `set`, `sha256_file`, `sorted`, `str`, `subprocess.check_output`, `subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip`, `wave2_path.is_file`, `write_ids`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 73 行：`parser.add_argument('--previous-eligibility-root', type=Path, default=Path('artifacts/b1_training_eligibility_v4'))`。
- 第 78 行：`parser.add_argument('--wave2-jsonl', type=Path, default=Path('artifacts/b1_d2_wave2_2000_teacher_v4/dataset/d2_valid.jsonl'))`。
- 第 86 行：`parser.add_argument('--wave2-freeze', type=Path, default=Path('artifacts/b1_d2_wave2_2000_teacher_v4/freeze_manifest.json'))`。
- 第 94 行：`parser.add_argument('--output-root', type=Path, default=Path('artifacts/b1_d2_cumulative_governance_v5'))`。

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

### `challenge/dataset/build_d2_cumulative_governance_v5.py`

来源 SHA256：`08061b30dd13eb898eb951b64bbfba1923d69b59827e104ebb932cd215f7b324`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 73 | `'--previous-eligibility-root'` | `type=Path; default=Path('artifacts/b1_training_eligibility_v4')` |
| 78 | `'--wave2-jsonl'` | `type=Path; default=Path('artifacts/b1_d2_wave2_2000_teacher_v4/dataset/d2_valid.jsonl')` |
| 86 | `'--wave2-freeze'` | `type=Path; default=Path('artifacts/b1_d2_wave2_2000_teacher_v4/freeze_manifest.json')` |
| 94 | `'--output-root'` | `type=Path; default=Path('artifacts/b1_d2_cumulative_governance_v5')` |

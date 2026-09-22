# build_manifest：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_manifest.py](../../../challenge/dataset/build_manifest.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_manifest

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_manifest.py 第 14 行](../../../challenge/dataset/build_manifest.py#L14)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `read_jsonl`

源码位置：[challenge/dataset/build_manifest.py 第 24 行](../../../challenge/dataset/build_manifest.py#L24)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

`read_jsonl` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `main`

源码位置：[challenge/dataset/build_manifest.py 第 52 行](../../../challenge/dataset/build_manifest.py#L52)。类型：`FunctionDef`。

```python
main() -> None
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `read_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.exists`, `path.open`, `rows.append`.
- `main` 调用：`Counter`, `Path`, `accepted_path.is_file`, `argparse.ArgumentParser`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `defaultdict`, `dict`, `isinstance`, `json.dumps`, `len`, `metadata.get`, `output_path.parent.mkdir`, `output_path.write_text`, `parser.add_argument`, `parser.parse_args`, `print`, `quality.get`, `read_jsonl`, `rejected_path.is_file`, `row.get`, `sample.get`, `sample_class.get`, `sha256_file`, `str`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `read_jsonl`，第 38 行：`ValueError(f'{path}:{line_no}: invalid JSON: {exc}')`。
- `read_jsonl`，第 43 行：`ValueError(f'{path}:{line_no}: row is not a JSON object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 55 行：`parser.add_argument('--accepted', required=True, help='accepted JSONL dataset')`。
- 第 61 行：`parser.add_argument('--rejected', required=True, help='rejected JSONL dataset')`。
- 第 67 行：`parser.add_argument('--output', required=True, help='manifest output path')`。
- 第 73 行：`parser.add_argument('--dataset-version', default='teacher_distill_v0.1_smoke')`。

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

### `challenge/dataset/build_manifest.py`

来源 SHA256：`8050345bc26ff16c8cb9ae35eba8feb58b24a434d0c6b01a454df8ff31677bf1`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 55 | `'--accepted'` | `required=True; help='accepted JSONL dataset'` |
| 61 | `'--rejected'` | `required=True; help='rejected JSONL dataset'` |
| 67 | `'--output'` | `required=True; help='manifest output path'` |
| 73 | `'--dataset-version'` | `default='teacher_distill_v0.1_smoke'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 38 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc` |
| `read_jsonl` / 43 | `not isinstance(row, dict)` | `raise ValueError(f'{path}:{line_no}: row is not a JSON object')` |

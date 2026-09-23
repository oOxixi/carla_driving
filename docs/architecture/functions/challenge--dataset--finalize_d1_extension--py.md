# finalize_d1_extension：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/finalize_d1_extension.py](../../../challenge/dataset/finalize_d1_extension.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

finalize_d1_extension

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/finalize_d1_extension.py 第 14 行](../../../challenge/dataset/finalize_d1_extension.py#L14)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `write_jsonl`

源码位置：[challenge/dataset/finalize_d1_extension.py 第 22 行](../../../challenge/dataset/finalize_d1_extension.py#L22)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows) -> 未声明返回类型
```

`write_jsonl` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `main`

源码位置：[challenge/dataset/finalize_d1_extension.py 第 36 行](../../../challenge/dataset/finalize_d1_extension.py#L36)。类型：`FunctionDef`。

```python
main() -> 未声明返回类型
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `main` 调用：`(out / 'finalization_provenance.json').write_text`, `(out / 'finalization_summary.json').write_text`, `(r.get('metadata') or {}).get`, `Counter`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `ap.add_argument`, `ap.parse_args`, `argparse.ArgumentParser`, `base.current_branch`, `base.current_head`, `base.read_jsonl`, `base.student_view_or_reason`, `base.validate_canonical`, `base.verify_tracked_file_matches_head`, `dict`, `group_owners.get`, `json.dumps`, `json.loads`, `len`, `m.get`, `meta.get`, `original_prov.get`, `p.is_file`, `print`, `provenance_path.read_text`, `provenance_path.relative_to`, `q.get`, `r.get`, `recovered.append`, `rejected_src.is_file`, `retained_quarantine.append`, `sample.get`, `set`, `sha256_file`, `str`, `write_jsonl`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 112 行：`RuntimeError(f'required file missing: {p}')`。
- `main`，第 133 行：`RuntimeError('existing valid sample missing group/extension id')`。
- `main`，第 138 行：`RuntimeError(f'base-extension group overlap: {g}')`。
- `main`，第 145 行：`RuntimeError(f'group {g} has owners {owner} and {eid}')`。
- `main`，第 171 行：`RuntimeError('attempted recovery overlaps base group: ' + str(g))`。
- `main`，第 218 行：`RuntimeError('duplicate sample_id after finalization')`。
- `main`，第 223 行：`RuntimeError('canonical/student count mismatch')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 39 行：`ap.add_argument('--base-dataset', default='artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl')`。
- 第 47 行：`ap.add_argument('--extension-dir', default='artifacts/b1_d1_extension_formal')`。
- 第 52 行：`ap.add_argument('--output-dir', default='artifacts/b1_d1_extension_final')`。
- 第 57 行：`ap.add_argument('--runner-python', default='/home/dcase_task2/miniconda3/envs/voice/bin/python')`。

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

### `challenge/dataset/finalize_d1_extension.py`

来源 SHA256：`013e3cd5583ae2087750b4e01f663750c9ca570c8109e40c11234ded93144b0e`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 39 | `'--base-dataset'` | `default='artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl'` |
| 47 | `'--extension-dir'` | `default='artifacts/b1_d1_extension_formal'` |
| 52 | `'--output-dir'` | `default='artifacts/b1_d1_extension_final'` |
| 57 | `'--runner-python'` | `default='/home/dcase_task2/miniconda3/envs/voice/bin/python'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 112 | `not p.is_file()` | `raise RuntimeError(f'required file missing: {p}')` |
| `main` / 133 | `not g or not eid` | `raise RuntimeError('existing valid sample missing group/extension id')` |
| `main` / 138 | `g in base_groups` | `raise RuntimeError(f'base-extension group overlap: {g}')` |
| `main` / 145 | `owner is not None and owner != eid` | `raise RuntimeError(f'group {g} has owners {owner} and {eid}')` |
| `main` / 171 | `g in base_groups` | `raise RuntimeError('attempted recovery overlaps base group: ' + str(g))` |
| `main` / 218 | `len(sample_ids) != len(set(sample_ids))` | `raise RuntimeError('duplicate sample_id after finalization')` |
| `main` / 223 | `len(final_valid) != len(final_student)` | `raise RuntimeError('canonical/student count mismatch')` |

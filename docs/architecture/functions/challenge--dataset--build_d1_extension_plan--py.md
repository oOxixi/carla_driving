# build_d1_extension_plan：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d1_extension_plan.py](../../../challenge/dataset/build_d1_extension_plan.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d1_extension_plan

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_d1_extension_plan.py 第 10 行](../../../challenge/dataset/build_d1_extension_plan.py#L10)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `canonical_json_sha256`

源码位置：[challenge/dataset/build_d1_extension_plan.py 第 17 行](../../../challenge/dataset/build_d1_extension_plan.py#L17)。类型：`FunctionDef`。

```python
canonical_json_sha256(value) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_jsonl`

源码位置：[challenge/dataset/build_d1_extension_plan.py 第 21 行](../../../challenge/dataset/build_d1_extension_plan.py#L21)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/build_d1_extension_plan.py 第 32 行](../../../challenge/dataset/build_d1_extension_plan.py#L32)。类型：`FunctionDef`。

```python
main() -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `canonical_json_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(raw).hexdigest`, `json.dumps`, `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode`.
- `read_jsonl` 调用：`RuntimeError`, `enumerate`, `isinstance`, `json.loads`, `path.read_text`, `path.read_text(encoding='utf-8').splitlines`, `raw.strip`, `rows.append`.
- `main` 调用：`(repo / args.base_dataset).resolve`, `(repo / args.base_provenance).resolve`, `(repo / args.output).resolve`, `(repo / args.registry).resolve`, `(row.get('metadata') or {}).get`, `Counter`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `ap.add_argument`, `ap.parse_args`, `argparse.ArgumentParser`, `base_ds.relative_to`, `base_prov.read_text`, `base_prov.relative_to`, `canonical_json_sha256`, `csv.DictReader`, `dict`, `eligible.append`, `int`, `json.dumps`, `json.loads`, `len`, `list`, `max`, `out.parent.mkdir`, `out.write_text`, `plan.append`, `print`, `prov.get`, `r.get`, `read_jsonl`, `reg.open`, `reg.relative_to`, `row.get`, `set`, `sha256_file`, `sorted`, `str`, `str(r.get('source_bucket') or '').upper`, `used_extension_seeds.add`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 50 行：`RuntimeError('--minimum-total must be >= 200')`。
- `main`，第 52 行：`RuntimeError('--target-total must be >= --minimum-total')`。
- `main`，第 54 行：`RuntimeError('--seed-start must be non-negative')`。
- `main`，第 61 行：`RuntimeError('base provenance is not formal')`。
- `main`，第 121 行：`RuntimeError(f'insufficient legal extension capacity: needed={needed}, planned={len(plan)}')`。
- `main`，第 127 行：`RuntimeError('extension seeds are not globally unique')`。
- `main`，第 130 行：`RuntimeError('extension seed overlaps formal base seed')`。
- `read_jsonl`，第 28 行：`RuntimeError(f'{path}:{n}: expected object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 34 行：`ap.add_argument('--registry', default='artifacts/b1_d1_registry_final/scenario_registry_v3.csv')`。
- 第 35 行：`ap.add_argument('--base-dataset', default='artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl')`。
- 第 36 行：`ap.add_argument('--base-provenance', default='artifacts/b1_d1_pinned_formal/provenance_manifest.json')`。
- 第 37 行：`ap.add_argument('--output', default='artifacts/b1_d1_extension_plan/d1_extension_plan_formal.json')`。
- 第 38 行：`ap.add_argument('--minimum-total', type=int, default=200)`。
- 第 39 行：`ap.add_argument('--target-total', type=int, default=220)`。
- 第 40 行：`ap.add_argument('--seed-start', type=int, default=1000000)`。

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

### `challenge/dataset/build_d1_extension_plan.py`

来源 SHA256：`f0fb5e40122d6e17fc8eedf5b72a79e7e442555f472c5919190c98173321fe17`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 34 | `'--registry'` | `default='artifacts/b1_d1_registry_final/scenario_registry_v3.csv'` |
| 35 | `'--base-dataset'` | `default='artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl'` |
| 36 | `'--base-provenance'` | `default='artifacts/b1_d1_pinned_formal/provenance_manifest.json'` |
| 37 | `'--output'` | `default='artifacts/b1_d1_extension_plan/d1_extension_plan_formal.json'` |
| 38 | `'--minimum-total'` | `type=int; default=200` |
| 39 | `'--target-total'` | `type=int; default=220` |
| 40 | `'--seed-start'` | `type=int; default=1000000` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 28 | `not isinstance(x, dict)` | `raise RuntimeError(f'{path}:{n}: expected object')` |
| `main` / 50 | `args.minimum_total < 200` | `raise RuntimeError('--minimum-total must be >= 200')` |
| `main` / 52 | `args.target_total < args.minimum_total` | `raise RuntimeError('--target-total must be >= --minimum-total')` |
| `main` / 54 | `args.seed_start < 0` | `raise RuntimeError('--seed-start must be non-negative')` |
| `main` / 61 | `prov.get('formal_code_gate') is not True` | `raise RuntimeError('base provenance is not formal')` |
| `main` / 121 | `len(plan) < needed` | `raise RuntimeError(f'insufficient legal extension capacity: needed={needed}, planned={len(plan)}')` |
| `main` / 127 | `len(used_extension_seeds) != len(plan)` | `raise RuntimeError('extension seeds are not globally unique')` |
| `main` / 130 | `base_seed_values & used_extension_seeds` | `raise RuntimeError('extension seed overlaps formal base seed')` |

# build_training_eligibility_v4：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_training_eligibility_v4.py](../../../challenge/dataset/build_training_eligibility_v4.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_training_eligibility_v4

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_training_eligibility_v4.py 第 18 行](../../../challenge/dataset/build_training_eligibility_v4.py#L18)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `canonical_sha256`

源码位置：[challenge/dataset/build_training_eligibility_v4.py 第 26 行](../../../challenge/dataset/build_training_eligibility_v4.py#L26)。类型：`FunctionDef`。

```python
canonical_sha256(obj: object) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_jsonl`

源码位置：[challenge/dataset/build_training_eligibility_v4.py 第 36 行](../../../challenge/dataset/build_training_eligibility_v4.py#L36)。类型：`FunctionDef`。

```python
load_jsonl(path: Path) -> list[dict]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_ids`

源码位置：[challenge/dataset/build_training_eligibility_v4.py 第 45 行](../../../challenge/dataset/build_training_eligibility_v4.py#L45)。类型：`FunctionDef`。

```python
write_ids(path: Path, ids: set[str]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/build_training_eligibility_v4.py 第 52 行](../../../challenge/dataset/build_training_eligibility_v4.py#L52)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `canonical_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(payload).hexdigest`, `json.dumps`, `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode`.
- `load_jsonl` 调用：`json.loads`, `line.strip`, `path.open`, `rows.append`.
- `write_ids` 调用：`''.join`, `path.write_text`, `sorted`.
- `main` 调用：`(out / 'training_eligibility_report.json').write_text`, `(row.get('quality') or {}).get`, `argparse.ArgumentParser`, `args.d1_jsonl.resolve`, `args.d2_jsonl.resolve`, `args.directional_quarantine_ids.resolve`, `args.output_root.resolve`, `canonical_sha256`, `d2_positive.isdisjoint`, `json.dumps`, `len`, `load_jsonl`, `out.mkdir`, `parser.add_argument`, `parser.parse_args`, `print`, `q_path.read_text`, `q_path.read_text(encoding='utf-8').splitlines`, `row.get`, `set`, `sha256_file`, `str`, `subprocess.check_output`, `subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip`, `write_ids`, `x.strip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 54 行：`parser.add_argument('--d1-jsonl', type=Path, required=True)`。
- 第 55 行：`parser.add_argument('--d2-jsonl', type=Path, required=True)`。
- 第 56 行：`parser.add_argument('--directional-quarantine-ids', type=Path, required=True)`。
- 第 61 行：`parser.add_argument('--output-root', type=Path, required=True)`。

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

### `challenge/dataset/build_training_eligibility_v4.py`

来源 SHA256：`54c36fafb9ed186d2370accecfbc40c7cc05fdb2844ee2261f8de03e196dc25b`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 54 | `'--d1-jsonl'` | `type=Path; required=True` |
| 55 | `'--d2-jsonl'` | `type=Path; required=True` |
| 56 | `'--directional-quarantine-ids'` | `type=Path; required=True` |
| 61 | `'--output-root'` | `type=Path; required=True` |

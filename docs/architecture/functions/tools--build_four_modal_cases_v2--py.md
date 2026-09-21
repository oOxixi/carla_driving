# build_four_modal_cases_v2：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/build_four_modal_cases_v2.py](../../../tools/build_four_modal_cases_v2.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Build an unambiguous v2 manifest while reusing immutable RGB/LiDAR files.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_read`

源码位置：[tools/build_four_modal_cases_v2.py 第 12 行](../../../tools/build_four_modal_cases_v2.py#L12)。类型：`FunctionDef`。

```python
_read(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_target_object`

源码位置：[tools/build_four_modal_cases_v2.py 第 20 行](../../../tools/build_four_modal_cases_v2.py#L20)。类型：`FunctionDef`。

```python
_target_object(row: dict[str, Any]) -> dict[str, Any] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_canonical_command`

源码位置：[tools/build_four_modal_cases_v2.py 第 34 行](../../../tools/build_four_modal_cases_v2.py#L34)。类型：`FunctionDef`。

```python
_canonical_command(target: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/build_four_modal_cases_v2.py 第 55 行](../../../tools/build_four_modal_cases_v2.py#L55)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_read` 调用：`json.loads`, `line.strip`, `path.read_text`, `path.read_text(encoding='utf-8').splitlines`.
- `_target_object` 调用：`item.get`, `next`, `row.get`, `row.get('expected', {}).get`, `row.get('perception', {}).get`.
- `_canonical_command` 调用：`float`, `round`, `str`, `str(target.get('class', '')).lower`, `str(target.get('relation', '')).lower`, `target.get`.
- `main` 调用：`''.join`, `Path`, `_canonical_command`, `_mutate_detector`, `_read`, `_target_object`, `argparse.ArgumentParser`, `args.dataset_dir.resolve`, `json.dumps`, `json.loads`, `len`, `output.is_absolute`, `output.write_text`, `output_rows.append`, `parser.add_argument`, `parser.parse_args`, `print`, `row.pop`, `row.setdefault`, `row['case_id'].removesuffix`, `row['case_id'].rsplit`, `str`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 57 行：`parser.add_argument('dataset_dir', type=Path)`。
- 第 58 行：`parser.add_argument('--output', type=Path, default=Path('cases_v2.jsonl'))`。

## 上下游与关联验证

静态导入的项目内实现：

- [tools/build_qwen_four_modal_stress_set.py](../../../tools/build_qwen_four_modal_stress_set.py)

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_four_modal_stress_set.py](../../../integration/tests/test_qwen_four_modal_stress_set.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/build_four_modal_cases_v2.py`

来源 SHA256：`5f4ca847b5b5e516b29e7bbc7a789c301ff9a403aae509753fa592b6d06ff1dd`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 57 | `'dataset_dir'` | `type=Path` |
| 58 | `'--output'` | `type=Path; default=Path('cases_v2.jsonl')` |

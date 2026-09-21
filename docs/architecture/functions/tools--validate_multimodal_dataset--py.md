# validate_multimodal_dataset：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/validate_multimodal_dataset.py](../../../tools/validate_multimodal_dataset.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Validate multimodal JSONL records without third-party dependencies.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_safe_relative_path`

源码位置：[tools/validate_multimodal_dataset.py 第 51 行](../../../tools/validate_multimodal_dataset.py#L51)。类型：`FunctionDef`。

```python
_safe_relative_path(value: str) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_iter_media_paths`

源码位置：[tools/validate_multimodal_dataset.py 第 62 行](../../../tools/validate_multimodal_dataset.py#L62)。类型：`FunctionDef`。

```python
_iter_media_paths(record: dict[str, Any]) -> Iterable[tuple[str, str]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_record`

源码位置：[tools/validate_multimodal_dataset.py 第 73 行](../../../tools/validate_multimodal_dataset.py#L73)。类型：`FunctionDef`。

```python
validate_record(record: Any, line_number: int) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_dataset`

源码位置：[tools/validate_multimodal_dataset.py 第 146 行](../../../tools/validate_multimodal_dataset.py#L146)。类型：`FunctionDef`。

```python
validate_dataset(jsonl_path: Path, *, dataset_root: Path | None=None, check_files: bool=False) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_dataset_files`

源码位置：[tools/validate_multimodal_dataset.py 第 196 行](../../../tools/validate_multimodal_dataset.py#L196)。类型：`FunctionDef`。

```python
validate_dataset_files(jsonl_paths: Iterable[Path], *, dataset_root: Path | None=None, check_files: bool=False) -> list[str]
```

Validate all split files together so cross-file leakage is visible.

### `main`

源码位置：[tools/validate_multimodal_dataset.py 第 244 行](../../../tools/validate_multimodal_dataset.py#L244)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_safe_relative_path` 调用：`PurePosixPath`, `bool`, `path.is_absolute`, `value.replace`.
- `_iter_media_paths` 调用：`isinstance`, `record.get`, `record.get('decision', {}).get`, `ref.get`, `sensors.get`.
- `validate_record` 调用：`', '.join`, `_iter_media_paths`, `_safe_relative_path`, `action.get`, `enumerate`, `errors.append`, `frame.get`, `isinstance`, `language.get`, `presence.get`, `quality.get`, `record.get`, `record.get(container_name, {}).get`, `record.keys`, `sensors.get`, `sorted`.
- `validate_dataset` 调用：`(dataset_root / relative).is_file`, `_iter_media_paths`, `_safe_relative_path`, `enumerate`, `errors.append`, `errors.extend`, `isinstance`, `json.loads`, `jsonl_path.open`, `raw_line.strip`, `record.get`, `sample_ids.add`, `sequence_splits.setdefault`, `set`, `validate_record`.
- `validate_dataset_files` 调用：`enumerate`, `errors.append`, `errors.extend`, `isinstance`, `json.loads`, `jsonl_path.open`, `raw_line.strip`, `record.get`, `sample_locations.setdefault`, `sequence_splits.setdefault`, `validate_dataset`.
- `main` 调用：`', '.join`, `argparse.ArgumentParser`, `len`, `parser.add_argument`, `parser.parse_args`, `print`, `str`, `validate_dataset_files`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 246 行：`parser.add_argument('jsonl', nargs='+', type=Path)`。
- 第 247 行：`parser.add_argument('--dataset-root', type=Path)`。
- 第 248 行：`parser.add_argument('--check-files', action='store_true')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_multimodal_dataset_builder.py](../../../integration/tests/test_multimodal_dataset_builder.py)
- [integration/tests/test_multimodal_dataset_validator.py](../../../integration/tests/test_multimodal_dataset_validator.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/validate_multimodal_dataset.py`

来源 SHA256：`e2cb74ad8cc9574a49329ef35931aa1ee3d4513c7e3c18ef6fd90d63d0d32eea`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 246 | `'jsonl'` | `nargs='+'; type=Path` |
| 247 | `'--dataset-root'` | `type=Path` |
| 248 | `'--check-files'` | `action='store_true'` |

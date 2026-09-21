# prepare_group1_voice_dataset：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/prepare_group1_voice_dataset.py](../../../tools/prepare_group1_voice_dataset.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Prepare the official Group 1 voice dataset for task 5/6 evaluation.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_sha256`

源码位置：[tools/prepare_group1_voice_dataset.py 第 27 行](../../../tools/prepare_group1_voice_dataset.py#L27)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_git_state`

源码位置：[tools/prepare_group1_voice_dataset.py 第 35 行](../../../tools/prepare_group1_voice_dataset.py#L35)。类型：`FunctionDef`。

```python
_git_state() -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_json`

源码位置：[tools/prepare_group1_voice_dataset.py 第 57 行](../../../tools/prepare_group1_voice_dataset.py#L57)。类型：`FunctionDef`。

```python
_load_json(path: Path) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_json`

源码位置：[tools/prepare_group1_voice_dataset.py 第 61 行](../../../tools/prepare_group1_voice_dataset.py#L61)。类型：`FunctionDef`。

```python
_write_json(path: Path, payload: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_archive_member_count`

源码位置：[tools/prepare_group1_voice_dataset.py 第 69 行](../../../tools/prepare_group1_voice_dataset.py#L69)。类型：`FunctionDef`。

```python
_archive_member_count(zip_path: Path, suffix: str) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_extract_if_needed`

源码位置：[tools/prepare_group1_voice_dataset.py 第 74 行](../../../tools/prepare_group1_voice_dataset.py#L74)。类型：`FunctionDef`。

```python
_extract_if_needed(zip_path: Path, extract_root: Path) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_normalize_archive_path`

源码位置：[tools/prepare_group1_voice_dataset.py 第 90 行](../../../tools/prepare_group1_voice_dataset.py#L90)。类型：`FunctionDef`。

```python
_normalize_archive_path(value: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_audio_entries`

源码位置：[tools/prepare_group1_voice_dataset.py 第 94 行](../../../tools/prepare_group1_voice_dataset.py#L94)。类型：`FunctionDef`。

```python
_audio_entries(record: dict[str, Any], condition: str) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_build_manifest`

源码位置：[tools/prepare_group1_voice_dataset.py 第 119 行](../../../tools/prepare_group1_voice_dataset.py#L119)。类型：`FunctionDef`。

```python
_build_manifest(records: list[dict[str, Any]], *, condition: str, audio_prefix: str, dataset_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_counter_to_dict`

源码位置：[tools/prepare_group1_voice_dataset.py 第 157 行](../../../tools/prepare_group1_voice_dataset.py#L157)。类型：`FunctionDef`。

```python
_counter_to_dict(counter: Counter[str]) -> dict[str, int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_manifest_stats`

源码位置：[tools/prepare_group1_voice_dataset.py 第 161 行](../../../tools/prepare_group1_voice_dataset.py#L161)。类型：`FunctionDef`。

```python
_manifest_stats(manifest: list[dict[str, Any]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_duplicate_texts`

源码位置：[tools/prepare_group1_voice_dataset.py 第 174 行](../../../tools/prepare_group1_voice_dataset.py#L174)。类型：`FunctionDef`。

```python
_duplicate_texts(records: list[dict[str, Any]]) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_label_conflicts`

源码位置：[tools/prepare_group1_voice_dataset.py 第 185 行](../../../tools/prepare_group1_voice_dataset.py#L185)。类型：`FunctionDef`。

```python
_label_conflicts(records: list[dict[str, Any]]) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_split_stats`

源码位置：[tools/prepare_group1_voice_dataset.py 第 204 行](../../../tools/prepare_group1_voice_dataset.py#L204)。类型：`FunctionDef`。

```python
_split_stats(dataset_root: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_markdown_report`

源码位置：[tools/prepare_group1_voice_dataset.py 第 226 行](../../../tools/prepare_group1_voice_dataset.py#L226)。类型：`FunctionDef`。

```python
_markdown_report(audit: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/prepare_group1_voice_dataset.py 第 286 行](../../../tools/prepare_group1_voice_dataset.py#L286)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `handle.read`, `hashlib.sha256`, `iter`, `path.open`.
- `_git_state` 调用：`bool`, `commit.stdout.strip`, `line.strip`, `status.stdout.splitlines`, `status.stdout.strip`, `subprocess.run`.
- `_load_json` 调用：`json.loads`, `path.read_text`.
- `_write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `_archive_member_count` 调用：`archive.namelist`, `name.endswith`, `sum`, `zipfile.ZipFile`.
- `_extract_if_needed` 调用：`all`, `archive.extractall`, `extract_root.mkdir`, `path.is_file`, `zipfile.ZipFile`.
- `_normalize_archive_path` 调用：`posixpath.normpath`, `value.replace`.
- `_audio_entries` 调用：`_normalize_archive_path`, `dialect.get`, `entries.append`, `mandarin.get`, `record.get`.
- `_build_manifest` 调用：`(dataset_root / rel_audio).is_file`, `_audio_entries`, `_normalize_archive_path`, `enumerate`, `manifest.append`, `missing.append`, `posixpath.join`, `record.get`.
- `_counter_to_dict` 调用：`counter.items`, `dict`, `sorted`.
- `_manifest_stats` 调用：`Counter`, `_counter_to_dict`, `len`.
- `_duplicate_texts` 调用：`defaultdict`, `grouped.items`, `grouped[record['text']].append`, `len`, `sorted`.
- `_label_conflicts` 调用：`defaultdict`, `grouped.items`, `grouped[record['text']].add`, `json.dumps`, `len`, `record.get`, `sorted`.
- `_split_stats` 调用：`Counter`, `_counter_to_dict`, `_load_json`, `item.get`, `len`, `path.is_file`, `set`, `sorted`, `split_texts.get`.
- `_markdown_report` 调用：`'\n'.join`.
- `main` 调用：`(output_root / 'GROUP1_TASK5_6_DATASET_PREP.md').write_text`, `_archive_member_count`, `_build_manifest`, `_duplicate_texts`, `_extract_if_needed`, `_git_state`, `_label_conflicts`, `_load_json`, `_manifest_stats`, `_markdown_report`, `_sha256`, `_split_stats`, `_write_json`, `argparse.ArgumentParser`, `args.extract_root.resolve`, `args.output_root.resolve`, `args.zip_path.resolve`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `len`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `print`, `str`, `zip_path.is_file`, `zip_path.stat`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 288 行：`parser.add_argument('--zip-path', type=Path, default=DEFAULT_ZIP)`。
- 第 289 行：`parser.add_argument('--extract-root', type=Path, default=DEFAULT_EXTRACT_ROOT)`。
- 第 290 行：`parser.add_argument('--output-root', type=Path, default=DEFAULT_OUTPUT_ROOT)`。
- 第 291 行：`parser.add_argument('--official-for-group1-tasks', action='store_true', default=True, help='Mark this archive as the official Group 1 audio drop in reports.')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/prepare_group1_voice_dataset.py`

来源 SHA256：`276fb3426e782eb74288dacf7434dcb84f49181604b0151d1c6a0bab2e52ab06`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 288 | `'--zip-path'` | `type=Path; default=DEFAULT_ZIP` |
| 289 | `'--extract-root'` | `type=Path; default=DEFAULT_EXTRACT_ROOT` |
| 290 | `'--output-root'` | `type=Path; default=DEFAULT_OUTPUT_ROOT` |
| 291 | `'--official-for-group1-tasks'` | `action='store_true'; default=True; help='Mark this archive as the official Group 1 audio drop in reports.'` |

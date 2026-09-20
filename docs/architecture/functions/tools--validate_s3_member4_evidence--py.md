# validate_s3_member4_evidence：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/validate_s3_member4_evidence.py](../../../tools/validate_s3_member4_evidence.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Validate member-4 S3 emergency-chain evidence from a real CARLA run.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_load_json`

源码位置：[tools/validate_s3_member4_evidence.py 第 17 行](../../../tools/validate_s3_member4_evidence.py#L17)。类型：`FunctionDef`。

```python
_load_json(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_jsonl`

源码位置：[tools/validate_s3_member4_evidence.py 第 24 行](../../../tools/validate_s3_member4_evidence.py#L24)。类型：`FunctionDef`。

```python
_load_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_extension_check`

源码位置：[tools/validate_s3_member4_evidence.py 第 38 行](../../../tools/validate_s3_member4_evidence.py#L38)。类型：`FunctionDef`。

```python
_extension_check(extension: Mapping[str, Any], key: str) -> Mapping[str, Any] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_evidence`

源码位置：[tools/validate_s3_member4_evidence.py 第 48 行](../../../tools/validate_s3_member4_evidence.py#L48)。类型：`FunctionDef`。

```python
validate_evidence(summary: Mapping[str, Any], records: list[Mapping[str, Any]], *, functional_only: bool=False) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_evidence.check`

源码位置：[tools/validate_s3_member4_evidence.py 第 56 行](../../../tools/validate_s3_member4_evidence.py#L56)。类型：`FunctionDef`。

```python
validate_evidence.check(key: str, passed: bool, actual: Any, required: Any, *, category: str='functional') -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/validate_s3_member4_evidence.py 第 255 行](../../../tools/validate_s3_member4_evidence.py#L255)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_load_json` 调用：`ValueError`, `isinstance`, `json.loads`, `path.read_text`.
- `_load_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.read_text`, `path.read_text(encoding='utf-8').splitlines`, `records.append`.
- `_extension_check` 调用：`extension.get`, `isinstance`, `item.get`, `next`.
- `validate_evidence` 调用：`Counter`, `REQUIRED_EVENTS.issubset`, `_extension_check`, `acceptance.get`, `all`, `any`, `bool`, `check`, `checks.append`, `config.get`, `dict`, `event.get`, `events.items`, `evidence.get`, `extension.get`, `float`, `identifiers.values`, `int`, `isinstance`, `item.get`, `item.get('latency', {}).get`, `item['longitudinal'].get`, `item['longitudinal']['risk'].get`, `len`, `metrics.get`, `model_id.upper`, `next`, `observed.get`, `qwen.get`, `sorted`, `start.get`, `str`, `str(item).upper`, `sum`, `summary.get`, `terminal_map.values`, `terminals.get`, `zip`.
- `main` 调用：`SystemExit`, `_load_json`, `_load_jsonl`, `argparse.ArgumentParser`, `args.jsonl.with_suffix`, `args.output.parent.mkdir`, `args.output.write_text`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `validate_evidence`.
- `check` 调用：`checks.append`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_load_json`，第 20 行：`ValueError(f'{path} must contain one JSON object')`。
- `_load_jsonl`，第 31 行：`ValueError(f'{path}:{line_number} must contain one JSON object')`。
- `_load_jsonl`，第 34 行：`ValueError(f'{path} contains no evidence records')`。
- `main`，第 273 行：`SystemExit(0 if report['passed'] else 1)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 257 行：`parser.add_argument('jsonl', type=Path, help='S3 ScenarioEvidenceRecorder JSONL')`。
- 第 258 行：`parser.add_argument('--summary', type=Path, help='Adjacent summary JSON path')`。
- 第 259 行：`parser.add_argument('--output', type=Path, help='Optional member-4 report path')`。
- 第 260 行：`parser.add_argument('--functional-only', action='store_true')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_validate_s3_member4_evidence.py](../../../integration/tests/test_validate_s3_member4_evidence.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/validate_s3_member4_evidence.py`

来源 SHA256：`9764bb845fdd1ba44719fb80892edd383d35be3b4583d36f13570fdba69e26ed`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 257 | `'jsonl'` | `type=Path; help='S3 ScenarioEvidenceRecorder JSONL'` |
| 258 | `'--summary'` | `type=Path; help='Adjacent summary JSON path'` |
| 259 | `'--output'` | `type=Path; help='Optional member-4 report path'` |
| 260 | `'--functional-only'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_load_json` / 20 | `not isinstance(value, dict)` | `raise ValueError(f'{path} must contain one JSON object')` |
| `_load_jsonl` / 31 | `not isinstance(value, dict)` | `raise ValueError(f'{path}:{line_number} must contain one JSON object')` |
| `_load_jsonl` / 34 | `not records` | `raise ValueError(f'{path} contains no evidence records')` |
| `main` / 273 | `本地无直接if；检查上下文` | `raise SystemExit(0 if report['passed'] else 1)` |

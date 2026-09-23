# validate_s2_member3_evidence：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/validate_s2_member3_evidence.py](../../../tools/validate_s2_member3_evidence.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Validate the member-3 S2 full-chain evidence bundle.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_load_json`

源码位置：[tools/validate_s2_member3_evidence.py 第 30 行](../../../tools/validate_s2_member3_evidence.py#L30)。类型：`FunctionDef`。

```python
_load_json(path: Path) -> dict[str, Any]
```

【_load_json】从参数、文件、环境或缓存解析维护工具的数据检查、生成、评测或证据处理所需输入；路径优先级、默认值和缺失处理以函数体为准，读取成功不自动证明内容身份正确。

### `_load_jsonl`

源码位置：[tools/validate_s2_member3_evidence.py 第 37 行](../../../tools/validate_s2_member3_evidence.py#L37)。类型：`FunctionDef`。

```python
_load_jsonl(path: Path) -> list[dict[str, Any]]
```

【_load_jsonl】从参数、文件、环境或缓存解析维护工具的数据检查、生成、评测或证据处理所需输入；路径优先级、默认值和缺失处理以函数体为准，读取成功不自动证明内容身份正确。

### `_extension_check`

源码位置：[tools/validate_s2_member3_evidence.py 第 51 行](../../../tools/validate_s2_member3_evidence.py#L51)。类型：`FunctionDef`。

```python
_extension_check(extension: Mapping[str, Any], key: str) -> Mapping[str, Any] | None
```

【_extension_check】检查维护工具的数据检查、生成、评测或证据处理的局部合同并返回/累计函数体定义的结果；静态校验通过不等于外部服务、CARLA、音频模型或最终交付已经通过。

### `validate_evidence`

源码位置：[tools/validate_s2_member3_evidence.py 第 61 行](../../../tools/validate_s2_member3_evidence.py#L61)。类型：`FunctionDef`。

```python
validate_evidence(summary: Mapping[str, Any], records: list[Mapping[str, Any]], *, functional_only: bool=False) -> dict[str, Any]
```

【validate_evidence】检查维护工具的数据检查、生成、评测或证据处理的局部合同并返回/累计函数体定义的结果；静态校验通过不等于外部服务、CARLA、音频模型或最终交付已经通过。

### `validate_evidence.check`

源码位置：[tools/validate_s2_member3_evidence.py 第 69 行](../../../tools/validate_s2_member3_evidence.py#L69)。类型：`FunctionDef`。

```python
validate_evidence.check(key: str, passed: bool, actual: Any, required: Any, *, category: str='functional') -> None
```

【validate_evidence.check】检查维护工具的数据检查、生成、评测或证据处理的局部合同并返回/累计函数体定义的结果；静态校验通过不等于外部服务、CARLA、音频模型或最终交付已经通过。

### `main`

源码位置：[tools/validate_s2_member3_evidence.py 第 222 行](../../../tools/validate_s2_member3_evidence.py#L222)。类型：`FunctionDef`。

```python
main() -> None
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `_load_json` 调用：`ValueError`, `isinstance`, `json.loads`, `path.read_text`.
- `_load_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.read_text`, `path.read_text(encoding='utf-8').splitlines`, `records.append`.
- `_extension_check` 调用：`extension.get`, `isinstance`, `item.get`, `next`.
- `validate_evidence` 调用：`EXPECTED_BEHAVIORS.issubset`, `_extension_check`, `acceptance.get`, `all`, `bool`, `check`, `checks.append`, `config.get`, `dict`, `extension.get`, `external_terminal_statuses.values`, `identifiers.values`, `isinstance`, `item.get`, `latency.get`, `len`, `list`, `metrics.get`, `next`, `qwen.get`, `qwen_checks.get`, `qwen_observed.get`, `sorted`, `start.get`, `str`, `str(item).upper`, `summary.get`, `terminal_counts.values`, `terminals.get`.
- `main` 调用：`SystemExit`, `_load_json`, `_load_jsonl`, `argparse.ArgumentParser`, `args.jsonl.with_suffix`, `args.output.parent.mkdir`, `args.output.write_text`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `validate_evidence`.
- `check` 调用：`checks.append`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_load_json`，第 33 行：`ValueError(f'{path} must contain one JSON object')`。
- `_load_jsonl`，第 44 行：`ValueError(f'{path}:{line_number} must contain one JSON object')`。
- `_load_jsonl`，第 47 行：`ValueError(f'{path} contains no evidence records')`。
- `main`，第 248 行：`SystemExit(0 if report['passed'] else 1)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 224 行：`parser.add_argument('jsonl', type=Path, help='S2 ScenarioEvidenceRecorder JSONL')`。
- 第 225 行：`parser.add_argument('--summary', type=Path, help='Adjacent summary JSON path')`。
- 第 226 行：`parser.add_argument('--output', type=Path, help='Optional member-3 report path')`。
- 第 227 行：`parser.add_argument('--functional-only', action='store_true', help='report the 150 ms performance result but do not use it to block functional-chain acceptance')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_validate_s2_member3_evidence.py](../../../integration/tests/test_validate_s2_member3_evidence.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/validate_s2_member3_evidence.py`

来源 SHA256：`b5bda9e090b5888220b7141a91cdd4e0d27edf03fb04a1401bb54fe6c222325c`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 224 | `'jsonl'` | `type=Path; help='S2 ScenarioEvidenceRecorder JSONL'` |
| 225 | `'--summary'` | `type=Path; help='Adjacent summary JSON path'` |
| 226 | `'--output'` | `type=Path; help='Optional member-3 report path'` |
| 227 | `'--functional-only'` | `action='store_true'; help='report the 150 ms performance result but do not use it to block functional-chain acceptance'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_load_json` / 33 | `not isinstance(value, dict)` | `raise ValueError(f'{path} must contain one JSON object')` |
| `_load_jsonl` / 44 | `not isinstance(value, dict)` | `raise ValueError(f'{path}:{line_number} must contain one JSON object')` |
| `_load_jsonl` / 47 | `not records` | `raise ValueError(f'{path} contains no evidence records')` |
| `main` / 248 | `本地无直接if；检查上下文` | `raise SystemExit(0 if report['passed'] else 1)` |

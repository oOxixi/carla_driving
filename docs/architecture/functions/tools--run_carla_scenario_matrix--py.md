# run_carla_scenario_matrix：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_carla_scenario_matrix.py](../../../tools/run_carla_scenario_matrix.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Repeat real-sensor CARLA scenarios across deterministic evidence seeds.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_latest_summary`

源码位置：[tools/run_carla_scenario_matrix.py 第 15 行](../../../tools/run_carla_scenario_matrix.py#L15)。类型：`FunctionDef`。

```python
_latest_summary(directory: Path) -> Path | None
```

【_latest_summary】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_record_from_summary`

源码位置：[tools/run_carla_scenario_matrix.py 第 20 行](../../../tools/run_carla_scenario_matrix.py#L20)。类型：`FunctionDef`。

```python
_record_from_summary(*, scenario: Path, seed: int, repeat: int, returncode: int, summary_path: Path | None, summary: dict[str, Any], resumed: bool=False) -> dict[str, Any]
```

【_record_from_summary】生成或记录维护工具的数据检查、生成、评测或证据处理的文件/元数据；执行前要核对目标路径与覆盖行为，执行后以内容哈希、返回码和消费方复核，不能仅以文件存在判定通过。

### `main`

源码位置：[tools/run_carla_scenario_matrix.py 第 51 行](../../../tools/run_carla_scenario_matrix.py#L51)。类型：`FunctionDef`。

```python
main() -> int
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `_latest_summary` 调用：`directory.glob`, `path.stat`, `sorted`.
- `_record_from_summary` 调用：`(summary.get('score') or {}).get`, `latency.get`, `str`, `summary.get`.
- `main` 调用：`(run_dir / 'console.log').write_text`, `Path`, `Path(__file__).resolve`, `_latest_summary`, `_record_from_summary`, `all`, `argparse.ArgumentParser`, `args.output_dir.mkdir`, `args.seeds.split`, `command.append`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `dict`, `env.get`, `existing.get`, `existing_summary.read_text`, `float`, `int`, `json.dumps`, `json.loads`, `len`, `max`, `min`, `os.pathsep.join`, `parser.add_argument`, `parser.parse_args`, `per_scenario.values`, `print`, `range`, `record.get`, `records.append`, `report_path.write_text`, `run_dir.mkdir`, `sorted`, `statistics.fmean`, `str`, `subprocess.run`, `sum`, `summary_path.read_text`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 53 行：`parser.add_argument('--scenario', action='append', required=True, type=Path)`。
- 第 54 行：`parser.add_argument('--seeds', default='0,1,2,3,4')`。
- 第 55 行：`parser.add_argument('--repeats-per-seed', type=int, default=4)`。
- 第 56 行：`parser.add_argument('--output-dir', required=True, type=Path)`。
- 第 57 行：`parser.add_argument('--carla-pythonpath', type=Path)`。
- 第 58 行：`parser.add_argument('--timeout-s', type=float, default=90.0)`。
- 第 59 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 60 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 61 行：`parser.add_argument('--scenario-facts-mode', choices=('perception', 'scenario', 'fuse'), default='perception')`。
- 第 66 行：`parser.add_argument('--resume', action='store_true')`。
- 第 67 行：`parser.add_argument('--use-current-map', action='store_true')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_scenario_matrix_tool.py](../../../integration/tests/test_scenario_matrix_tool.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_carla_scenario_matrix.py`

来源 SHA256：`4fc299c1ed3b82fc3d399cd8aa27f06c43fde5cdaad475fa67fd28de3b72163e`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 53 | `'--scenario'` | `action='append'; required=True; type=Path` |
| 54 | `'--seeds'` | `default='0,1,2,3,4'` |
| 55 | `'--repeats-per-seed'` | `type=int; default=4` |
| 56 | `'--output-dir'` | `required=True; type=Path` |
| 57 | `'--carla-pythonpath'` | `type=Path` |
| 58 | `'--timeout-s'` | `type=float; default=90.0` |
| 59 | `'--host'` | `default='127.0.0.1'` |
| 60 | `'--port'` | `type=int; default=2000` |
| 61 | `'--scenario-facts-mode'` | `choices=('perception', 'scenario', 'fuse'); default='perception'` |
| 66 | `'--resume'` | `action='store_true'` |
| 67 | `'--use-current-map'` | `action='store_true'` |

# repro_cli：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/repro_cli.py](../../../tools/repro_cli.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Container-side entry point for the independent reproduction package.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `EvaluationDecision.status: str`；默认：`未在声明处设置`。
- `EvaluationDecision.remaining_steps: list[str]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `EvaluationDecision`

源码位置：[tools/repro_cli.py 第 32 行](../../../tools/repro_cli.py#L32)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `EvaluationDecision.from_latency_p95`

源码位置：[tools/repro_cli.py 第 37 行](../../../tools/repro_cli.py#L37)。类型：`FunctionDef`。

```python
EvaluationDecision.from_latency_p95(cls, latency_p95_ms: float) -> 'EvaluationDecision'
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_evaluation_steps`

源码位置：[tools/repro_cli.py 第 43 行](../../../tools/repro_cli.py#L43)。类型：`FunctionDef`。

```python
build_evaluation_steps() -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_command`

源码位置：[tools/repro_cli.py 第 47 行](../../../tools/repro_cli.py#L47)。类型：`FunctionDef`。

```python
run_command(command: list[str], cwd: Path | None=None) -> subprocess.CompletedProcess[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_json`

源码位置：[tools/repro_cli.py 第 51 行](../../../tools/repro_cli.py#L51)。类型：`FunctionDef`。

```python
_write_json(path: Path, payload: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_sha256`

源码位置：[tools/repro_cli.py 第 58 行](../../../tools/repro_cli.py#L58)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_required_data`

源码位置：[tools/repro_cli.py 第 66 行](../../../tools/repro_cli.py#L66)。类型：`FunctionDef`。

```python
_required_data(data_root: Path) -> dict[str, Path]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_run_checked`

源码位置：[tools/repro_cli.py 第 75 行](../../../tools/repro_cli.py#L75)。类型：`FunctionDef`。

```python
_run_checked(command: list[str], runner: CommandRunner, log_path: Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_preflight`

源码位置：[tools/repro_cli.py 第 86 行](../../../tools/repro_cli.py#L86)。类型：`FunctionDef`。

```python
_preflight(data_root: Path, run_root: Path, qwen_log: Path | None, carla_log: Path | None, runner: CommandRunner) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_scenario_command`

源码位置：[tools/repro_cli.py 第 120 行](../../../tools/repro_cli.py#L120)。类型：`FunctionDef`。

```python
_scenario_command(data_root: Path, scenario: str, run_root: Path) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_run_mode`

源码位置：[tools/repro_cli.py 第 134 行](../../../tools/repro_cli.py#L134)。类型：`FunctionDef`。

```python
_run_mode(args: argparse.Namespace, runner: CommandRunner) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `parse_args`

源码位置：[tools/repro_cli.py 第 231 行](../../../tools/repro_cli.py#L231)。类型：`FunctionDef`。

```python
parse_args(argv: Sequence[str] | None=None) -> argparse.Namespace
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/repro_cli.py 第 243 行](../../../tools/repro_cli.py#L243)。类型：`FunctionDef`。

```python
main(argv: Sequence[str] | None=None, *, runner: CommandRunner=run_command) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `build_evaluation_steps` 调用：`list`.
- `run_command` 调用：`subprocess.run`.
- `_write_json` 调用：`json.dumps`, `os.replace`, `path.parent.mkdir`, `path.with_suffix`, `temp.write_text`.
- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `_run_checked` 调用：`' '.join`, `RuntimeError`, `log_path.parent.mkdir`, `log_path.write_text`, `runner`.
- `_preflight` 调用：`'; '.join`, `(gpu.stderr or gpu.stdout).strip`, `FileNotFoundError`, `RuntimeError`, `_required_data`, `_sha256`, `_write_json`, `carla_log.is_file`, `gpu.stdout.strip`, `os.environ.get`, `path.is_file`, `qwen_log.is_file`, `required.items`, `runner`, `shutil.copy2`, `verify_kernel_log`.
- `_scenario_command` 调用：`os.environ.get`, `str`.
- `_run_mode` 调用：`(args.output_root / 'runs').iterdir`, `(context.logs_dir / 'full-chain.log').write_text`, `(evaluate_run / 'metrics/full_chain.json').read_text`, `(path / 'metrics/full_chain.json').is_file`, `AssertionError`, `EvaluationDecision.from_latency_p95`, `Path`, `RuntimeError`, `ValueError`, `_preflight`, `_required_data`, `_run_checked`, `_scenario_command`, `_write_json`, `begin_run`, `finish_run`, `float`, `image_dir.glob`, `json.loads`, `latest.parent.mkdir`, `latest.write_text`, `os.environ.get`, `print`, `report_path.is_file`, `report_path.read_text`, `runner`, `sorted`, `str`, `type`.
- `parse_args` 调用：`Path`, `argparse.ArgumentParser`, `parser.add_argument`, `parser.parse_args`.
- `main` 调用：`_run_mode`, `parse_args`.
- `from_latency_p95` 调用：`cls`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_preflight`，第 91 行：`FileNotFoundError('missing frozen release data: ' + '; '.join(missing))`。
- `_preflight`，第 97 行：`RuntimeError('nvidia-smi failed: ' + (gpu.stderr or gpu.stdout).strip())`。
- `_preflight`，第 101 行：`FileNotFoundError(f'Qwen bootstrap log missing: {qwen_log}')`。
- `_preflight`，第 106 行：`FileNotFoundError(f'CARLA bootstrap log missing: {carla_log}')`。
- `_run_checked`，第 83 行：`RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}")`。
- `_run_mode`，第 171 行：`RuntimeError(f'full-chain evaluation produced no report (exit {result.returncode})')`。
- `_run_mode`，第 185 行：`RuntimeError(f'full-chain evaluation failed official gates (exit {result.returncode})')`。
- `_run_mode`，第 201 行：`ValueError('stability requires an existing evaluate run or --evaluate-run')`。
- `_run_mode`，第 206 行：`ValueError(f'stability requires prior end-to-end P95 <= 150 ms; got {p95:.3f}')`。
- `_run_mode`，第 224 行：`AssertionError(args.mode)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 233 行：`parser.add_argument('mode', choices=('preflight', 'smoke', 'evaluate', 'demo', 'stability'))`。
- 第 234 行：`parser.add_argument('--profile', choices=('rtx5070', 'a800-safe', 'a800-optimized'), default='rtx5070')`。
- 第 235 行：`parser.add_argument('--data-root', type=Path, default=Path('/app/release_data'))`。
- 第 236 行：`parser.add_argument('--output-root', type=Path, default=Path('/output'))`。
- 第 237 行：`parser.add_argument('--qwen-log', type=Path)`。
- 第 238 行：`parser.add_argument('--carla-log', type=Path)`。
- 第 239 行：`parser.add_argument('--evaluate-run', type=Path)`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/run_manifest.py](../../../integration/run_manifest.py)
- [tools/verify_qwen_kernel.py](../../../tools/verify_qwen_kernel.py)

静态 import 消费者（含测试）：

- [integration/tests/test_repro_delivery.py](../../../integration/tests/test_repro_delivery.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/repro_cli.py`

来源 SHA256：`22ba76f6596b033d1205dab24a495e0ad71f52020da05e4c4b30164808733a5d`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `EvaluationDecision.status` | `str` | `无声明默认；构造/赋值方提供` |
| `EvaluationDecision.remaining_steps` | `list[str]` | `无声明默认；构造/赋值方提供` |

CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 233 | `'mode'` | `choices=('preflight', 'smoke', 'evaluate', 'demo', 'stability')` |
| 234 | `'--profile'` | `choices=('rtx5070', 'a800-safe', 'a800-optimized'); default='rtx5070'` |
| 235 | `'--data-root'` | `type=Path; default=Path('/app/release_data')` |
| 236 | `'--output-root'` | `type=Path; default=Path('/output')` |
| 237 | `'--qwen-log'` | `type=Path` |
| 238 | `'--carla-log'` | `type=Path` |
| 239 | `'--evaluate-run'` | `type=Path` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_run_checked` / 83 | `result.returncode` | `raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}")` |
| `_preflight` / 91 | `missing` | `raise FileNotFoundError('missing frozen release data: ' + '; '.join(missing))` |
| `_preflight` / 97 | `gpu.returncode` | `raise RuntimeError('nvidia-smi failed: ' + (gpu.stderr or gpu.stdout).strip())` |
| `_preflight` / 101 | `qwen_log is not None AND not qwen_log.is_file()` | `raise FileNotFoundError(f'Qwen bootstrap log missing: {qwen_log}')` |
| `_preflight` / 106 | `carla_log is not None AND not carla_log.is_file()` | `raise FileNotFoundError(f'CARLA bootstrap log missing: {carla_log}')` |
| `_run_mode` / 171 | `args.mode == 'evaluate' AND not report_path.is_file()` | `raise RuntimeError(f'full-chain evaluation produced no report (exit {result.returncode})')` |
| `_run_mode` / 185 | `args.mode == 'evaluate' AND result.returncode not in {0, 3}` | `raise RuntimeError(f'full-chain evaluation failed official gates (exit {result.returncode})')` |
| `_run_mode` / 201 | `args.mode == 'stability' AND evaluate_run is None AND not candidates` | `raise ValueError('stability requires an existing evaluate run or --evaluate-run')` |
| `_run_mode` / 206 | `args.mode == 'stability' AND p95 > 150.0` | `raise ValueError(f'stability requires prior end-to-end P95 <= 150 ms; got {p95:.3f}')` |
| `_run_mode` / 224 | `本地无直接if；检查上下文` | `raise AssertionError(args.mode)` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `tools/repro_cli.py:112` | `'QWEN_PROFILE'` | `'qwen3vl-2b-int4'` |
| `tools/repro_cli.py:123` | `'QWEN_BASE_URL'` | `'http://qwen:8001/v1'` |
| `tools/repro_cli.py:124` | `'QWEN_MODEL'` | `'h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4'` |
| `tools/repro_cli.py:138` | `'RELEASE_COMMIT'` | `'unknown'` |
| `tools/repro_cli.py:156` | `'QWEN_PROFILE'` | `'qwen3vl-2b-int4'` |
| `tools/repro_cli.py:159` | `'QWEN_BASE_URL'` | `'http://qwen:8001/v1'` |
| `tools/repro_cli.py:211` | `'CARLA_HOST'` | `'carla'` |
| `tools/repro_cli.py:212` | `'CARLA_PORT'` | `'2000'` |
| `tools/repro_cli.py:213` | `'QWEN_BASE_URL'` | `'http://qwen:8001/v1'` |
| `tools/repro_cli.py:214` | `'QWEN_PROFILE'` | `'qwen3vl-2b-int4'` |
| `tools/repro_cli.py:215` | `'QWEN_MODEL'` | `'h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4'` |

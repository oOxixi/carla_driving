# official_scenario_runner：功能记录

上级模块：[模块说明](../modules/vehicle-scenarios.md) · 实现：[integration/official_scenario_runner.py](../../../integration/official_scenario_runner.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [场景触发、车辆行为与验收分离](scenario-evidence-contract.md)

## 功能职责与范围

Pinned CARLA ScenarioRunner 0.9.16 process boundary.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ScenarioRunnerInvocation.root: Path`；默认：`未在声明处设置`。
- `ScenarioRunnerInvocation.scenario: str`；默认：`未在声明处设置`。
- `ScenarioRunnerInvocation.host: str`；默认：`'127.0.0.1'`。
- `ScenarioRunnerInvocation.port: int`；默认：`2000`。
- `ScenarioRunnerInvocation.timeout_s: float`；默认：`60.0`。
- `ScenarioRunnerInvocation.python_executable: str`；默认：`sys.executable`。
- `ScenarioRunnerInvocation.agent_path: Path | None`；默认：`None`。
- `ScenarioRunnerInvocation.agent_config: Path | None`；默认：`None`。
- `ScenarioRunnerInvocation.sync: bool`；默认：`True`。
- `ScenarioRunnerInvocation.reload_world: bool`；默认：`False`。
- `ScenarioRunnerInvocation.output: bool`；默认：`True`。
- `ScenarioRunnerInvocation.json_output: bool`；默认：`True`。
- `ScenarioRunnerInvocation.extra_args: tuple[str, ...]`；默认：`()`。

## 功能入口：输入、输出与实现说明

### `ScenarioRunnerInvocation`

源码位置：[integration/official_scenario_runner.py 第 21 行](../../../integration/official_scenario_runner.py#L21)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ScenarioRunnerInvocation.__post_init__`

源码位置：[integration/official_scenario_runner.py 第 36 行](../../../integration/official_scenario_runner.py#L36)。类型：`FunctionDef`。

```python
ScenarioRunnerInvocation.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_checkout`

源码位置：[integration/official_scenario_runner.py 第 47 行](../../../integration/official_scenario_runner.py#L47)。类型：`FunctionDef`。

```python
verify_checkout(root: str | Path) -> str
```

Fail unless ``root`` is the exact pinned ScenarioRunner checkout.

### `build_command`

源码位置：[integration/official_scenario_runner.py 第 69 行](../../../integration/official_scenario_runner.py#L69)。类型：`FunctionDef`。

```python
build_command(invocation: ScenarioRunnerInvocation, *, verify: bool=True) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run`

源码位置：[integration/official_scenario_runner.py 第 97 行](../../../integration/official_scenario_runner.py#L97)。类型：`FunctionDef`。

```python
run(invocation: ScenarioRunnerInvocation, *, check: bool=True) -> subprocess.CompletedProcess[str]
```

Run the verified external orchestrator without using a shell.

## 内部调用与异常路径

- `verify_checkout` 调用：`FileNotFoundError`, `Path`, `Path(root).resolve`, `RuntimeError`, `completed.stdout.strip`, `completed.stdout.strip().lower`, `entry.is_file`, `str`, `subprocess.run`.
- `build_command` 调用：`command.append`, `command.extend`, `invocation.agent_config.resolve`, `invocation.agent_path.resolve`, `invocation.root.resolve`, `str`, `verify_checkout`.
- `run` 调用：`build_command`, `subprocess.run`.
- `__post_init__` 调用：`ValueError`, `self.host.strip`, `self.scenario.strip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 38 行：`ValueError('scenario must be non-empty')`。
- `__post_init__`，第 40 行：`ValueError('host must be non-empty and port must be in 1..65535')`。
- `__post_init__`，第 42 行：`ValueError('timeout_s must be positive')`。
- `__post_init__`，第 44 行：`ValueError('agent_config requires agent_path')`。
- `verify_checkout`，第 52 行：`FileNotFoundError(f'ScenarioRunner entry not found: {entry}. Run scripts/fetch_scenario_runner.ps1 first.')`。
- `verify_checkout`，第 63 行：`RuntimeError(f"ScenarioRunner commit mismatch: expected {SCENARIO_RUNNER_COMMIT}, got {commit or '<empty>'}")`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_official_scenario_runner.py](../../../integration/tests/test_official_scenario_runner.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/official_scenario_runner.py`

来源 SHA256：`5d464376f8661192bc3cbfcbb33d0277ce488c7b7004cc940a36d4c2f6b52126`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ScenarioRunnerInvocation.root` | `Path` | `无声明默认；构造/赋值方提供` |
| `ScenarioRunnerInvocation.scenario` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioRunnerInvocation.host` | `str` | `'127.0.0.1'` |
| `ScenarioRunnerInvocation.port` | `int` | `2000` |
| `ScenarioRunnerInvocation.timeout_s` | `float` | `60.0` |
| `ScenarioRunnerInvocation.python_executable` | `str` | `sys.executable` |
| `ScenarioRunnerInvocation.agent_path` | `Path &#124; None` | `None` |
| `ScenarioRunnerInvocation.agent_config` | `Path &#124; None` | `None` |
| `ScenarioRunnerInvocation.sync` | `bool` | `True` |
| `ScenarioRunnerInvocation.reload_world` | `bool` | `False` |
| `ScenarioRunnerInvocation.output` | `bool` | `True` |
| `ScenarioRunnerInvocation.json_output` | `bool` | `True` |
| `ScenarioRunnerInvocation.extra_args` | `tuple[str, ...]` | `()` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `ScenarioRunnerInvocation.__post_init__` / 38 | `not self.scenario.strip()` | `raise ValueError('scenario must be non-empty')` |
| `ScenarioRunnerInvocation.__post_init__` / 40 | `not self.host.strip() or not 1 <= self.port <= 65535` | `raise ValueError('host must be non-empty and port must be in 1..65535')` |
| `ScenarioRunnerInvocation.__post_init__` / 42 | `self.timeout_s <= 0.0` | `raise ValueError('timeout_s must be positive')` |
| `ScenarioRunnerInvocation.__post_init__` / 44 | `self.agent_config is not None and self.agent_path is None` | `raise ValueError('agent_config requires agent_path')` |
| `verify_checkout` / 52 | `not entry.is_file()` | `raise FileNotFoundError(f'ScenarioRunner entry not found: {entry}. Run scripts/fetch_scenario_runner.ps1 first.')` |
| `verify_checkout` / 63 | `commit != SCENARIO_RUNNER_COMMIT` | `raise RuntimeError(f"ScenarioRunner commit mismatch: expected {SCENARIO_RUNNER_COMMIT}, got {commit or '<empty>'}")` |

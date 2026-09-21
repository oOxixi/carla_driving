# validate_route_generalization：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/validate_route_generalization.py](../../../tools/validate_route_generalization.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Validate destination route planning against one or more live CARLA maps.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_map_name`

源码位置：[tools/validate_route_generalization.py 第 21 行](../../../tools/validate_route_generalization.py#L21)。类型：`FunctionDef`。

```python
_map_name(world_map: Any) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_candidate_pairs`

源码位置：[tools/validate_route_generalization.py 第 25 行](../../../tools/validate_route_generalization.py#L25)。类型：`FunctionDef`。

```python
_candidate_pairs(spawn_points: list[Any], minimum_endpoint_gap_m: float) -> list[tuple[int, Any, int, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_route_profiles`

源码位置：[tools/validate_route_generalization.py 第 47 行](../../../tools/validate_route_generalization.py#L47)。类型：`FunctionDef`。

```python
_route_profiles(route: Any) -> tuple[tuple[str, ...], dict[str, object]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_select_diverse_routes`

源码位置：[tools/validate_route_generalization.py 第 86 行](../../../tools/validate_route_generalization.py#L86)。类型：`FunctionDef`。

```python
_select_diverse_routes(candidates: list[dict[str, object]], count: int) -> list[dict[str, object]]
```

Greedily retain deterministic routes that add structural coverage.

### `validate_map`

源码位置：[tools/validate_route_generalization.py 第 115 行](../../../tools/validate_route_generalization.py#L115)。类型：`FunctionDef`。

```python
validate_map(client: Any, map_name: str, pairs_required: int, *, minimum_endpoint_gap_m: float, minimum_route_length_m: float, maximum_route_length_m: float, maximum_junction_count: int | None, required_profiles: tuple[str, ...]=(), candidate_limit: int=120) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/validate_route_generalization.py 第 204 行](../../../tools/validate_route_generalization.py#L204)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_map_name` 调用：`getattr`, `str`, `str(getattr(world_map, 'name', 'unknown')).rsplit`.
- `_candidate_pairs` 调用：`len`, `math.hypot`, `max`, `pairs.append`, `range`.
- `_route_profiles` 调用：`abs`, `estimate_curvature`, `float`, `int`, `len`, `max`, `profiles.add`, `range`, `route.reference.metadata.get`, `sorted`, `tuple`.
- `_select_diverse_routes` 调用：`covered.update`, `destinations.add`, `enumerate`, `float`, `int`, `len`, `list`, `max`, `remaining.remove`, `selected.append`, `set`, `starts.add`, `str`.
- `validate_map` 调用：`Counter`, `RouteManager`, `_candidate_pairs`, `_map_name`, `_route_profiles`, `_select_diverse_routes`, `candidates.append`, `client.get_world`, `client.load_world`, `dict`, `failures.append`, `float`, `len`, `list`, `manager.plan`, `manager.state`, `reason_counts.items`, `set`, `sorted`, `state.to_dict`, `str`, `world.get_map`, `world_map.get_spawn_points`.
- `main` 调用：`SystemExit`, `all`, `argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `bool`, `carla.Client`, `client.set_timeout`, `float`, `json.dumps`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `print`, `tuple`, `validate_map`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 236 行：`SystemExit(f'CARLA Python API is required: {error}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 206 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 207 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 208 行：`parser.add_argument('--timeout-s', type=float, default=30.0)`。
- 第 209 行：`parser.add_argument('--maps', nargs='+', default=['Town03_Opt', 'Town05'])`。
- 第 210 行：`parser.add_argument('--pairs-per-map', type=int, default=3)`。
- 第 211 行：`parser.add_argument('--minimum-endpoint-gap-m', type=float, default=100.0)`。
- 第 212 行：`parser.add_argument('--minimum-route-length-m', type=float, default=0.0)`。
- 第 213 行：`parser.add_argument('--maximum-route-length-m', type=float, default=float('inf'))`。
- 第 214 行：`parser.add_argument('--maximum-junction-count', type=int)`。
- 第 215 行：`parser.add_argument('--required-profiles', nargs='*', default=(), choices=('straight', 'curved', 'junction_free', 'junction', 'multi_junction', 'short_route', 'medium_route', 'long_route', 'multi_road', 'lane_change'))`。
- 第 225 行：`parser.add_argument('--candidate-limit', type=int, default=120)`。
- 第 226 行：`parser.add_argument('--output', type=Path)`。

## 上下游与关联验证

静态导入的项目内实现：

- [car_control_B/path_utils.py](../../../car_control_B/path_utils.py)
- [integration/route_manager.py](../../../integration/route_manager.py)

静态 import 消费者（含测试）：

- [integration/tests/test_route_generalization_tool.py](../../../integration/tests/test_route_generalization_tool.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/validate_route_generalization.py`

来源 SHA256：`adb90dd72b2b802c15ce821271f50af95addefe09d7c85d8246af595280e6d89`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 206 | `'--host'` | `default='127.0.0.1'` |
| 207 | `'--port'` | `type=int; default=2000` |
| 208 | `'--timeout-s'` | `type=float; default=30.0` |
| 209 | `'--maps'` | `nargs='+'; default=['Town03_Opt', 'Town05']` |
| 210 | `'--pairs-per-map'` | `type=int; default=3` |
| 211 | `'--minimum-endpoint-gap-m'` | `type=float; default=100.0` |
| 212 | `'--minimum-route-length-m'` | `type=float; default=0.0` |
| 213 | `'--maximum-route-length-m'` | `type=float; default=float('inf')` |
| 214 | `'--maximum-junction-count'` | `type=int` |
| 215 | `'--required-profiles'` | `nargs='*'; default=(); choices=('straight', 'curved', 'junction_free', 'junction', 'multi_junction', 'short_route', 'medium_route', 'long_route', 'multi_road', 'lane_change')` |
| 225 | `'--candidate-limit'` | `type=int; default=120` |
| 226 | `'--output'` | `type=Path` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 236 | `except ImportError` | `raise SystemExit(f'CARLA Python API is required: {error}') from error` |

# probe_s2_route_anchor：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/probe_s2_route_anchor.py](../../../tools/probe_s2_route_anchor.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Probe Town spawn points against the S2 out-and-back lane-change profile.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_location_at_distance`

源码位置：[tools/probe_s2_route_anchor.py 第 15 行](../../../tools/probe_s2_route_anchor.py#L15)。类型：`FunctionDef`。

```python
_location_at_distance(carla_api, route, target_m: float) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/probe_s2_route_anchor.py 第 31 行](../../../tools/probe_s2_route_anchor.py#L31)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_location_at_distance` 调用：`carla_api.Location`, `math.dist`, `zip`.
- `main` 调用：`ValueError`, `_location_at_distance`, `argparse.ArgumentParser`, `args.candidates.split`, `args.inspect_location.split`, `build_lane_change_route_reference`, `build_route_reference`, `carla.Client`, `carla.Location`, `client.get_world`, `client.load_world`, `client.set_timeout`, `completed.append`, `direction.lower`, `float`, `int`, `len`, `list`, `parser.add_argument`, `parser.parse_args`, `passed.append`, `print`, `range`, `str`, `type`, `value.strip`, `waypoint.get_left_lane`, `waypoint.get_right_lane`, `world.get_map`, `world.get_map().name.endswith`, `world_map.get_spawn_points`, `world_map.get_waypoint`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 57 行：`ValueError('--inspect-location must be x,y,z')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 33 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 34 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 35 行：`parser.add_argument('--map', default='Town03_Opt')`。
- 第 36 行：`parser.add_argument('--candidates', default='')`。
- 第 37 行：`parser.add_argument('--sample-step-m', type=int, default=40)`。
- 第 38 行：`parser.add_argument('--sample-end-m', type=int, default=200)`。
- 第 39 行：`parser.add_argument('--inspect-location', help='optional CARLA world x,y,z location to inspect instead of spawn anchors')`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/route_planner.py](../../../integration/route_planner.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/probe_s2_route_anchor.py`

来源 SHA256：`82a265de0ea504886e2d7800c04a9d8ad1e5ad172c6182589bc57f41a3327b81`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 33 | `'--host'` | `default='127.0.0.1'` |
| 34 | `'--port'` | `type=int; default=2000` |
| 35 | `'--map'` | `default='Town03_Opt'` |
| 36 | `'--candidates'` | `default=''` |
| 37 | `'--sample-step-m'` | `type=int; default=40` |
| 38 | `'--sample-end-m'` | `type=int; default=200` |
| 39 | `'--inspect-location'` | `help='optional CARLA world x,y,z location to inspect instead of spawn anchors'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 57 | `args.inspect_location AND len(values) != 3` | `raise ValueError('--inspect-location must be x,y,z')` |

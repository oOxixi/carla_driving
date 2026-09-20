# capture_qwen_test_image：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/capture_qwen_test_image.py](../../../tools/capture_qwen_test_image.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

capture_qwen_test_image

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `parse_args`

源码位置：[tools/capture_qwen_test_image.py 第 13 行](../../../tools/capture_qwen_test_image.py#L13)。类型：`FunctionDef`。

```python
parse_args() -> argparse.Namespace
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `save_carla_image_as_jpeg`

源码位置：[tools/capture_qwen_test_image.py 第 61 行](../../../tools/capture_qwen_test_image.py#L61)。类型：`FunctionDef`。

```python
save_carla_image_as_jpeg(carla_image: carla.Image, output_path: Path) -> None
```

把 CARLA BGRA 图像转换成标准 RGB JPEG。

### `find_spawn_transform`

源码位置：[tools/capture_qwen_test_image.py 第 105 行](../../../tools/capture_qwen_test_image.py#L105)。类型：`FunctionDef`。

```python
find_spawn_transform(world: carla.World, spawn_index: int) -> carla.Transform
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `spawn_ego`

源码位置：[tools/capture_qwen_test_image.py 第 119 行](../../../tools/capture_qwen_test_image.py#L119)。类型：`FunctionDef`。

```python
spawn_ego(world: carla.World, preferred_transform: carla.Transform) -> carla.Vehicle
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `spawn_static_lead_vehicle`

源码位置：[tools/capture_qwen_test_image.py 第 167 行](../../../tools/capture_qwen_test_image.py#L167)。类型：`FunctionDef`。

```python
spawn_static_lead_vehicle(world: carla.World, ego: carla.Vehicle, distance_m: float) -> Optional[carla.Vehicle]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `create_front_camera`

源码位置：[tools/capture_qwen_test_image.py 第 246 行](../../../tools/capture_qwen_test_image.py#L246)。类型：`FunctionDef`。

```python
create_front_camera(world: carla.World, ego: carla.Vehicle, *, width: int, height: int, fov: float) -> carla.Sensor
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `drain_latest_image`

源码位置：[tools/capture_qwen_test_image.py 第 298 行](../../../tools/capture_qwen_test_image.py#L298)。类型：`FunctionDef`。

```python
drain_latest_image(image_queue: queue.Queue, latest: Optional[carla.Image]) -> Optional[carla.Image]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/capture_qwen_test_image.py 第 311 行](../../../tools/capture_qwen_test_image.py#L311)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `parse_args` 调用：`argparse.ArgumentParser`, `parser.add_argument`, `parser.parse_args`.
- `save_carla_image_as_jpeg` 调用：`Image.fromarray`, `Image.fromarray(rgb).save`, `RuntimeError`, `np.frombuffer`, `output_path.parent.mkdir`, `raw.reshape`.
- `find_spawn_transform` 调用：`RuntimeError`, `len`, `world.get_map`, `world.get_map().get_spawn_points`.
- `spawn_ego` 调用：`RuntimeError`, `blueprint_library.filter`, `list`, `ordered_points.extend`, `vehicle_bp.has_attribute`, `vehicle_bp.set_attribute`, `world.get_blueprint_library`, `world.get_map`, `world.get_map().get_spawn_points`, `world.try_spawn_actor`.
- `spawn_static_lead_vehicle` 调用：`blueprint_library.filter`, `carla.VehicleControl`, `ego.get_location`, `ego_waypoint.next`, `lead.apply_control`, `lead_bp.has_attribute`, `lead_bp.set_attribute`, `list`, `print`, `world.get_blueprint_library`, `world.get_map`, `world.try_spawn_actor`, `world_map.get_waypoint`.
- `create_front_camera` 调用：`camera_bp.set_attribute`, `carla.Location`, `carla.Rotation`, `carla.Transform`, `str`, `world.get_blueprint_library`, `world.get_blueprint_library().find`, `world.spawn_actor`.
- `drain_latest_image` 调用：`image_queue.get_nowait`.
- `main` 调用：`Path`, `Path(args.output).expanduser`, `Path(args.output).expanduser().resolve`, `RuntimeError`, `actor.destroy`, `actors.append`, `camera.listen`, `camera.stop`, `carla.Client`, `carla.Location`, `carla.Rotation`, `carla.Transform`, `carla.VehicleControl`, `client.get_world`, `client.load_world`, `client.set_timeout`, `create_front_camera`, `current_map_name.split`, `drain_latest_image`, `ego.apply_control`, `ego.get_transform`, `find_spawn_transform`, `image_queue.get`, `image_queue.put`, `lead.get_transform`, `parse_args`, `print`, `queue.Queue`, `range`, `reversed`, `save_carla_image_as_jpeg`, `spawn_ego`, `spawn_static_lead_vehicle`, `spectator.set_transform`, `world.apply_settings`, `world.get_map`, `world.get_settings`, `world.get_spectator`, `world.get_weather`, `world.set_weather`, `world.tick`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `find_spawn_transform`，第 112 行：`RuntimeError('当前地图没有可用车辆出生点')`。
- `main`，第 491 行：`RuntimeError('RGB 相机没有返回图像。请检查 CARLA 是否使用 -nullrhi 或 no_rendering_mode。')`。
- `save_carla_image_as_jpeg`，第 76 行：`RuntimeError(f'图像数据大小异常：实际 {raw.size}，预期 {expected_size}')`。
- `spawn_ego`，第 135 行：`RuntimeError('没有找到车辆蓝图')`。
- `spawn_ego`，第 161 行：`RuntimeError('所有出生点都被占用，无法生成自车。请确认没有残留车辆。')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 18 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 19 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 20 行：`parser.add_argument('--timeout-s', type=float, default=30.0)`。
- 第 22 行：`parser.add_argument('--map', default=None, help='可选地图名，例如 Town03_Opt；省略时使用当前地图')`。
- 第 27 行：`parser.add_argument('--spawn-index', type=int, default=0)`。
- 第 29 行：`parser.add_argument('--output', default='artifacts/runtime/qwen_test.jpg')`。
- 第 34 行：`parser.add_argument('--width', type=int, default=800)`。
- 第 35 行：`parser.add_argument('--height', type=int, default=450)`。
- 第 36 行：`parser.add_argument('--fov', type=float, default=100.0)`。
- 第 38 行：`parser.add_argument('--map-warmup-frames', type=int, default=40, help='优化地图瓦片加载预热帧数')`。
- 第 44 行：`parser.add_argument('--sensor-warmup-frames', type=int, default=10, help='相机挂载后的预热帧数')`。
- 第 51 行：`parser.add_argument('--lead-distance-m', type=float, default=18.0, help='在自车前方生成一辆静止前车；小于等于0表示不生成')`。

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

### `tools/capture_qwen_test_image.py`

来源 SHA256：`c73a93c566d4c8b137046f2ec2bb769984169af8851afa63431e4389e7c1bfa7`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 18 | `'--host'` | `default='127.0.0.1'` |
| 19 | `'--port'` | `type=int; default=2000` |
| 20 | `'--timeout-s'` | `type=float; default=30.0` |
| 22 | `'--map'` | `default=None; help='可选地图名，例如 Town03_Opt；省略时使用当前地图'` |
| 27 | `'--spawn-index'` | `type=int; default=0` |
| 29 | `'--output'` | `default='artifacts/runtime/qwen_test.jpg'` |
| 34 | `'--width'` | `type=int; default=800` |
| 35 | `'--height'` | `type=int; default=450` |
| 36 | `'--fov'` | `type=float; default=100.0` |
| 38 | `'--map-warmup-frames'` | `type=int; default=40; help='优化地图瓦片加载预热帧数'` |
| 44 | `'--sensor-warmup-frames'` | `type=int; default=10; help='相机挂载后的预热帧数'` |
| 51 | `'--lead-distance-m'` | `type=float; default=18.0; help='在自车前方生成一辆静止前车；小于等于0表示不生成'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `save_carla_image_as_jpeg` / 76 | `raw.size != expected_size` | `raise RuntimeError(f'图像数据大小异常：实际 {raw.size}，预期 {expected_size}')` |
| `find_spawn_transform` / 112 | `not spawn_points` | `raise RuntimeError('当前地图没有可用车辆出生点')` |
| `spawn_ego` / 135 | `not candidates` | `raise RuntimeError('没有找到车辆蓝图')` |
| `spawn_ego` / 161 | `本地无直接if；检查上下文` | `raise RuntimeError('所有出生点都被占用，无法生成自车。请确认没有残留车辆。')` |
| `main` / 491 | `latest_image is None` | `raise RuntimeError('RGB 相机没有返回图像。请检查 CARLA 是否使用 -nullrhi 或 no_rendering_mode。')` |

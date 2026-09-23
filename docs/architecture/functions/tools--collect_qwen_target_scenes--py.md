# collect_qwen_target_scenes：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/collect_qwen_target_scenes.py](../../../tools/collect_qwen_target_scenes.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Collect real CARLA RGB frames with deterministic multi-vehicle annotations.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_jsonl`

源码位置：[tools/collect_qwen_target_scenes.py 第 18 行](../../../tools/collect_qwen_target_scenes.py#L18)。类型：`FunctionDef`。

```python
_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

【_jsonl】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_sha256`

源码位置：[tools/collect_qwen_target_scenes.py 第 25 行](../../../tools/collect_qwen_target_scenes.py#L25)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

【_sha256】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_same_direction`

源码位置：[tools/collect_qwen_target_scenes.py 第 33 行](../../../tools/collect_qwen_target_scenes.py#L33)。类型：`FunctionDef`。

```python
_same_direction(first: carla.Waypoint, second: carla.Waypoint) -> bool
```

【_same_direction】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_adjacent_waypoint`

源码位置：[tools/collect_qwen_target_scenes.py 第 39 行](../../../tools/collect_qwen_target_scenes.py#L39)。类型：`FunctionDef`。

```python
_adjacent_waypoint(waypoint: carla.Waypoint) -> tuple[carla.Waypoint | None, str]
```

【_adjacent_waypoint】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_lifted`

源码位置：[tools/collect_qwen_target_scenes.py 第 53 行](../../../tools/collect_qwen_target_scenes.py#L53)。类型：`FunctionDef`。

```python
_lifted(transform: carla.Transform, z_offset: float=0.35) -> carla.Transform
```

【_lifted】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_distance`

源码位置：[tools/collect_qwen_target_scenes.py 第 61 行](../../../tools/collect_qwen_target_scenes.py#L61)。类型：`FunctionDef`。

```python
_distance(first: carla.Location, second: carla.Location) -> float
```

【_distance】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_camera_intrinsic`

源码位置：[tools/collect_qwen_target_scenes.py 第 68 行](../../../tools/collect_qwen_target_scenes.py#L68)。类型：`FunctionDef`。

```python
_camera_intrinsic(width: int, height: int, fov_degrees: float) -> np.ndarray
```

【_camera_intrinsic】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_project_bbox`

源码位置：[tools/collect_qwen_target_scenes.py 第 77 行](../../../tools/collect_qwen_target_scenes.py#L77)。类型：`FunctionDef`。

```python
_project_bbox(actor: carla.Actor, camera: carla.Sensor, width: int, height: int, fov_degrees: float) -> list[float] | None
```

【_project_bbox】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_spawn_actor`

源码位置：[tools/collect_qwen_target_scenes.py 第 113 行](../../../tools/collect_qwen_target_scenes.py#L113)。类型：`FunctionDef`。

```python
_spawn_actor(world: carla.World, blueprint: carla.ActorBlueprint, transform: carla.Transform) -> carla.Actor
```

【_spawn_actor】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_select_layout`

源码位置：[tools/collect_qwen_target_scenes.py 第 125 行](../../../tools/collect_qwen_target_scenes.py#L125)。类型：`FunctionDef`。

```python
_select_layout(world_map: carla.Map, spawn_points: list[carla.Transform], seed: int, *, occlusion: bool) -> tuple[carla.Transform, carla.Waypoint, carla.Waypoint, str]
```

【_select_layout】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_collect_one`

源码位置：[tools/collect_qwen_target_scenes.py 第 158 行](../../../tools/collect_qwen_target_scenes.py#L158)。类型：`FunctionDef`。

```python
_collect_one(world: carla.World, seed: int, image_dir: Path, width: int, height: int, fov: float, actors: list[carla.Actor], *, weather_profile: str, pedestrian_second: bool, occlusion: bool, dense_target_count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]
```

【_collect_one】按函数体组合维护工具的数据检查、生成、评测或证据处理的中间对象或产物；输入筛选、排序、身份和失败项必须保留，生成成功不代表后续运行或评分门禁通过。

### `_front_corridor_min`

源码位置：[tools/collect_qwen_target_scenes.py 第 420 行](../../../tools/collect_qwen_target_scenes.py#L420)。类型：`FunctionDef`。

```python
_front_corridor_min(points: np.ndarray) -> float | None
```

Summarize raw CARLA LiDAR for the high-level four-modal context.

### `main`

源码位置：[tools/collect_qwen_target_scenes.py 第 436 行](../../../tools/collect_qwen_target_scenes.py#L436)。类型：`FunctionDef`。

```python
main() -> int
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `_jsonl` 调用：`''.join`, `json.dumps`, `path.write_text`.
- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `handle.read`, `hashlib.sha256`, `iter`, `path.open`.
- `_same_direction` 调用：`first.transform.get_forward_vector`, `second.transform.get_forward_vector`.
- `_adjacent_waypoint` 调用：`_same_direction`, `waypoint.get_left_lane`, `waypoint.get_right_lane`.
- `_lifted` 调用：`carla.Location`, `carla.Transform`.
- `_distance` 调用：`math.sqrt`.
- `_camera_intrinsic` 调用：`math.radians`, `math.tan`, `np.identity`.
- `_project_bbox` 调用：`_camera_intrinsic`, `actor.bounding_box.get_world_vertices`, `actor.get_transform`, `camera.get_transform`, `camera.get_transform().get_inverse_matrix`, `float`, `max`, `min`, `np.array`, `pixels.append`, `round`.
- `_spawn_actor` 调用：`RuntimeError`, `_lifted`, `actor.set_simulate_physics`, `world.try_spawn_actor`.
- `_select_layout` 调用：`RuntimeError`, `_adjacent_waypoint`, `ego_waypoint.next`, `len`, `range`, `world_map.get_waypoint`.
- `_collect_one` 调用：`RuntimeError`, `_distance`, `_front_corridor_min`, `_lifted`, `_project_bbox`, `_select_layout`, `_sha256`, `_spawn_actor`, `actor.get_location`, `actors.append`, `blueprint.get_attribute`, `blueprint.get_attribute('number_of_wheels').as_int`, `blueprints.filter`, `blueprints.find`, `camera.listen`, `camera_blueprint.set_attribute`, `carla.Location`, `carla.Transform`, `dense_actor.set_simulate_physics`, `ego.get_location`, `ego_waypoint.next`, `frames.empty`, `frames.get`, `frames.get_nowait`, `image.save_to_disk`, `int`, `len`, `lidar.listen`, `lidar_blueprint.set_attribute`, `lidar_frames.get`, `lidar_path.mkdir`, `max`, `np.frombuffer`, `np.frombuffer(lidar_measurement.raw_data, dtype=np.float32).reshape`, `np.frombuffer(lidar_measurement.raw_data, dtype=np.float32).reshape((-1, 4)).copy`, `np.save`, `objects.append`, `queue.Queue`, `random.Random`, `range`, `rng.randrange`, `round`, `sorted`, `str`, `target_specs.append`, `world.get_blueprint_library`, `world.get_map`, `world.get_map().get_spawn_points`, `world.get_map().get_waypoint`, `world.spawn_actor`, `world.tick`, `world.try_spawn_actor`.
- `_front_corridor_min` 调用：`ValueError`, `float`, `np.abs`, `np.any`, `np.min`, `round`.
- `main` 调用：`(output_dir / 'collection_report.json').write_text`, `ValueError`, `_collect_one`, `_jsonl`, `actor.destroy`, `argparse.ArgumentParser`, `args.occlusion_seeds.split`, `args.output_dir.resolve`, `args.pedestrian_seeds.split`, `args.seeds.split`, `args.weather_profiles.split`, `carla.Client`, `carla.WeatherParameters`, `cases.extend`, `client.get_world`, `client.set_timeout`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `image_dir.mkdir`, `int`, `item.strip`, `json.dumps`, `len`, `parser.add_argument`, `parser.parse_args`, `print`, `reversed`, `scenes.append`, `sorted`, `world.apply_settings`, `world.get_map`, `world.get_settings`, `world.get_weather`, `world.set_weather`, `world.tick`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_collect_one`，第 204 行：`RuntimeError('no pedestrian blueprint is available')`。
- `_collect_one`，第 291 行：`RuntimeError(f'could not align RGB/LiDAR frames: rgb={image.frame}, lidar={lidar_measurement.frame}')`。
- `_collect_one`，第 326 行：`RuntimeError(f'target {label} is not visible for seed {seed}')`。
- `_front_corridor_min`，第 423 行：`ValueError('LiDAR points must be an Nx4-like array')`。
- `_select_layout`，第 155 行：`RuntimeError('no usable two-target road layout found')`。
- `_spawn_actor`，第 120 行：`RuntimeError(f'could not spawn actor at {transform.location}')`。
- `main`，第 483 行：`ValueError('at least one weather profile is required')`。
- `main`，第 485 行：`ValueError('dense-target-count must be in [2, 8]')`。
- `main`，第 528 行：`ValueError(f'unknown weather profile: {weather_profile!r}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 438 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 439 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 440 行：`parser.add_argument('--output-dir', required=True, type=Path)`。
- 第 441 行：`parser.add_argument('--seeds', default='0,1,2,3,4')`。
- 第 442 行：`parser.add_argument('--width', type=int, default=800)`。
- 第 443 行：`parser.add_argument('--height', type=int, default=450)`。
- 第 444 行：`parser.add_argument('--fov', type=float, default=90.0)`。
- 第 445 行：`parser.add_argument('--weather-profiles', default='clear_day', help='comma-separated cycle: clear_day,hard_rain,night,fog,sunset')`。
- 第 450 行：`parser.add_argument('--pedestrian-seeds', default='', help='comma-separated seeds whose second target is a pedestrian')`。
- 第 455 行：`parser.add_argument('--occlusion-seeds', default='', help='comma-separated seeds using two same-lane vehicles')`。
- 第 460 行：`parser.add_argument('--dense-target-count', type=int, default=2, help='total projected actors per scene; values above two add same-lane distractors')`。

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

### `tools/collect_qwen_target_scenes.py`

来源 SHA256：`02c38c5c6c17d0958ab4e8180cf78c035af07b3a3edc7d6eaf195536ce26692e`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 438 | `'--host'` | `default='127.0.0.1'` |
| 439 | `'--port'` | `type=int; default=2000` |
| 440 | `'--output-dir'` | `required=True; type=Path` |
| 441 | `'--seeds'` | `default='0,1,2,3,4'` |
| 442 | `'--width'` | `type=int; default=800` |
| 443 | `'--height'` | `type=int; default=450` |
| 444 | `'--fov'` | `type=float; default=90.0` |
| 445 | `'--weather-profiles'` | `default='clear_day'; help='comma-separated cycle: clear_day,hard_rain,night,fog,sunset'` |
| 450 | `'--pedestrian-seeds'` | `default=''; help='comma-separated seeds whose second target is a pedestrian'` |
| 455 | `'--occlusion-seeds'` | `default=''; help='comma-separated seeds using two same-lane vehicles'` |
| 460 | `'--dense-target-count'` | `type=int; default=2; help='total projected actors per scene; values above two add same-lane distractors'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_spawn_actor` / 120 | `actor is None` | `raise RuntimeError(f'could not spawn actor at {transform.location}')` |
| `_select_layout` / 155 | `本地无直接if；检查上下文` | `raise RuntimeError('no usable two-target road layout found')` |
| `_collect_one` / 204 | `pedestrian_second AND not walker_blueprints` | `raise RuntimeError('no pedestrian blueprint is available')` |
| `_collect_one` / 291 | `lidar_measurement.frame != image.frame` | `raise RuntimeError(f'could not align RGB/LiDAR frames: rgb={image.frame}, lidar={lidar_measurement.frame}')` |
| `_collect_one` / 326 | `bbox is None` | `raise RuntimeError(f'target {label} is not visible for seed {seed}')` |
| `_front_corridor_min` / 423 | `points.ndim != 2 or points.shape[1] < 3` | `raise ValueError('LiDAR points must be an Nx4-like array')` |
| `main` / 483 | `not weather_profiles` | `raise ValueError('at least one weather profile is required')` |
| `main` / 485 | `args.dense_target_count < 2 or args.dense_target_count > 8` | `raise ValueError('dense-target-count must be in [2, 8]')` |
| `main` / 528 | `except KeyError` | `raise ValueError(f'unknown weather profile: {weather_profile!r}') from error` |

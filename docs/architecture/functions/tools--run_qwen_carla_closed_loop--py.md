# run_qwen_carla_closed_loop：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run one auditable RGB/LiDAR -> Qwen -> A/B/C/D -> CARLA loop.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_parser`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 31 行](../../../tools/run_qwen_carla_closed_loop.py#L31)。类型：`FunctionDef`。

```python
_parser() -> argparse.ArgumentParser
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_map_leaf`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 54 行](../../../tools/run_qwen_carla_closed_loop.py#L54)。类型：`FunctionDef`。

```python
_map_leaf(name: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_speed_mps`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 58 行](../../../tools/run_qwen_carla_closed_loop.py#L58)。类型：`FunctionDef`。

```python
_speed_mps(vector: Any) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_vehicle_state`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 62 行](../../../tools/run_qwen_carla_closed_loop.py#L62)。类型：`FunctionDef`。

```python
_vehicle_state(ego: Any, frame: int, sim_time_s: float, world_map: Any) -> RuntimeVehicleState
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_lateral_controller`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 78 行](../../../tools/run_qwen_carla_closed_loop.py#L78)。类型：`FunctionDef`。

```python
_lateral_controller() -> PurePursuitController
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_spawn_ego`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 90 行](../../../tools/run_qwen_carla_closed_loop.py#L90)。类型：`FunctionDef`。

```python
_spawn_ego(session: CarlaSession, world: Any) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_acquire_ready_sample`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 105 行](../../../tools/run_qwen_carla_closed_loop.py#L105)。类型：`FunctionDef`。

```python
_acquire_ready_sample(session: CarlaSession, world: Any, bridge: CarlaPerceptionBridge, *, attempts: int=12, timeout_s: float=10.0) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_save_sensor_pair`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 128 行](../../../tools/run_qwen_carla_closed_loop.py#L128)。类型：`FunctionDef`。

```python
_save_sensor_pair(sample: Any, media_dir: Path) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_sha256`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 148 行](../../../tools/run_qwen_carla_closed_loop.py#L148)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_json_dump`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 156 行](../../../tools/run_qwen_carla_closed_loop.py#L156)。类型：`FunctionDef`。

```python
_json_dump(path: Path, value: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_json_line`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 164 行](../../../tools/run_qwen_carla_closed_loop.py#L164)。类型：`FunctionDef`。

```python
_json_line(stream: Any, value: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 169 行](../../../tools/run_qwen_carla_closed_loop.py#L169)。类型：`FunctionDef`。

```python
run(args: argparse.Namespace) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_qwen_carla_closed_loop.py 第 438 行](../../../tools/run_qwen_carla_closed_loop.py#L438)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_parser` 调用：`argparse.ArgumentParser`, `parser.add_argument`.
- `_map_leaf` 调用：`str`, `str(name).replace`, `str(name).replace('\\', '/').rstrip`, `str(name).replace('\\', '/').rstrip('/').split`.
- `_speed_mps` 调用：`float`, `math.hypot`.
- `_vehicle_state` 调用：`RuntimeVehicleState`, `_speed_mps`, `ego.get_transform`, `ego.get_velocity`, `float`, `str`, `world_map.get_waypoint`.
- `_lateral_controller` 调用：`PurePursuitController`, `PurePursuitParams`.
- `_spawn_ego` 调用：`RuntimeError`, `blueprint.has_attribute`, `blueprint.set_attribute`, `library.filter`, `list`, `session.track_actor`, `world.get_blueprint_library`, `world.get_map`, `world.get_map().get_spawn_points`, `world.try_spawn_actor`.
- `_acquire_ready_sample` 调用：`RuntimeError`, `bridge.acquire`, `range`, `session.tick`, `world.get_snapshot`.
- `_save_sensor_pair` 调用：`ValueError`, `_sha256`, `int`, `media_dir.mkdir`, `np.frombuffer`, `np.save`, `points.reshape`, `sample.rgb.save_to_disk`, `str`.
- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `_json_dump` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `_json_line` 调用：`json.dumps`, `stream.flush`, `stream.write`.
- `run` 调用：`CarlaPerceptionBridge`, `CarlaSession`, `ControlRuntime`, `FileNotFoundError`, `Path`, `QwenInputContext`, `RuntimeError`, `StrictQwenVLAdapter.from_local_checkpoint`, `ValueError`, `_acquire_ready_sample`, `_json_dump`, `_json_line`, `_lateral_controller`, `_map_leaf`, `_map_leaf(args.expected_map).lower`, `_map_leaf(world_map.name).lower`, `_save_sensor_pair`, `_spawn_ego`, `_speed_mps`, `_vehicle_state`, `abs`, `adapter`, `args.model_path.expanduser`, `args.model_path.expanduser().resolve`, `args.output_dir.expanduser`, `args.output_dir.expanduser().resolve`, `asdict`, `attach_default_sensors`, `bridge.acquire`, `build_command`, `build_route_reference`, `carla.Client`, `carla.VehicleControl`, `client.get_server_version`, `client.get_world`, `client.set_timeout`, `context.to_payload`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `dict`, `ego.apply_control`, `ego.get_location`, `ego.get_velocity`, `float`, `frame_log_path.open`, `initial_sample.safety_summary.to_dict`, `len`, `math.hypot`, `max`, `media_records.append`, `min`, `model_path.is_dir`, `output_dir.mkdir`, `range`, `result.final_control.to_dict`, `runtime.lateral.reset`, `runtime.step`, `runtime.submit_voice`, `safety_payload.update`, `sample.safety_summary.to_dict`, `sensor_specs_for_profile`, `session.tick`, `state.to_dict`, `str`, `time.monotonic_ns`, `world.get_map`, `world.get_snapshot`, `world.get_weather`.
- `main` 调用：`_json_dump`, `_parser`, `_parser().parse_args`, `args.output_dir.mkdir`, `json.dumps`, `print`, `run`, `str`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_acquire_ready_sample`，第 125 行：`RuntimeError(f'RGB/LiDAR did not become ready: {last_error}')`。
- `_save_sensor_pair`，第 136 行：`ValueError('CARLA LiDAR buffer is not XYZI float32')`。
- `_spawn_ego`，第 94 行：`RuntimeError('CARLA has no vehicle blueprint')`。
- `_spawn_ego`，第 102 行：`RuntimeError('unable to spawn the closed-loop ego vehicle')`。
- `run`，第 171 行：`ValueError('frames and media-stride must be positive')`。
- `run`，第 177 行：`ValueError('fixed-delta and sensor-timeout must be positive; target speed must be non-negative')`。
- `run`，第 192 行：`RuntimeError(f'current CARLA map is {world_map.name!r}; expected {args.expected_map!r}')`。
- `run`，第 198 行：`FileNotFoundError(f'Qwen model not found: {model_path}')`。
- `run`，第 266 行：`RuntimeError('Qwen completed without a trace backed by a real RGB image')`。
- `run`，第 313 行：`RuntimeError(f'Qwen command rejected by A: {adapted.feedback}')`。
- `run`，第 394 行：`RuntimeError('closed loop produced no final evidence')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 33 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 34 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 35 行：`parser.add_argument('--expected-map', default='Town03_Opt')`。
- 第 36 行：`parser.add_argument('--model-path', type=Path, required=True)`。
- 第 37 行：`parser.add_argument('--output-dir', type=Path, required=True)`。
- 第 38 行：`parser.add_argument('--command', default='请以每秒4米的速度沿当前道路直行')`。
- 第 39 行：`parser.add_argument('--frames', type=int, default=120)`。
- 第 40 行：`parser.add_argument('--fixed-delta', type=float, default=0.05)`。
- 第 41 行：`parser.add_argument('--sensor-timeout', type=float, default=10.0)`。
- 第 42 行：`parser.add_argument('--target-speed-mps', type=float, default=4.0)`。
- 第 43 行：`parser.add_argument('--media-stride', type=int, default=10)`。
- 第 44 行：`parser.add_argument('--sensor-profile', choices=('low', 'default'), default='low')`。
- 第 45 行：`parser.add_argument('--max-new-tokens', type=int, default=48)`。
- 第 46 行：`parser.add_argument('--awq-backend', choices=('auto', 'torch_awq', 'gemm', 'gemm_triton'), default='auto')`。

## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [integration/carla_perception.py](../../../integration/carla_perception.py)
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_command_adapter.py](../../../integration/qwen_command_adapter.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)
- [integration/route_planner.py](../../../integration/route_planner.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_qwen_carla_closed_loop.py`

来源 SHA256：`0ad89c5aec4789c7df262809d5d22af7f256ec8bc4dd1c80ceae4fa6cfde299c`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 33 | `'--host'` | `default='127.0.0.1'` |
| 34 | `'--port'` | `type=int; default=2000` |
| 35 | `'--expected-map'` | `default='Town03_Opt'` |
| 36 | `'--model-path'` | `type=Path; required=True` |
| 37 | `'--output-dir'` | `type=Path; required=True` |
| 38 | `'--command'` | `default='请以每秒4米的速度沿当前道路直行'` |
| 39 | `'--frames'` | `type=int; default=120` |
| 40 | `'--fixed-delta'` | `type=float; default=0.05` |
| 41 | `'--sensor-timeout'` | `type=float; default=10.0` |
| 42 | `'--target-speed-mps'` | `type=float; default=4.0` |
| 43 | `'--media-stride'` | `type=int; default=10` |
| 44 | `'--sensor-profile'` | `choices=('low', 'default'); default='low'` |
| 45 | `'--max-new-tokens'` | `type=int; default=48` |
| 46 | `'--awq-backend'` | `choices=('auto', 'torch_awq', 'gemm', 'gemm_triton'); default='auto'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_spawn_ego` / 94 | `not candidates` | `raise RuntimeError('CARLA has no vehicle blueprint')` |
| `_spawn_ego` / 102 | `本地无直接if；检查上下文` | `raise RuntimeError('unable to spawn the closed-loop ego vehicle')` |
| `_acquire_ready_sample` / 125 | `本地无直接if；检查上下文` | `raise RuntimeError(f'RGB/LiDAR did not become ready: {last_error}')` |
| `_save_sensor_pair` / 136 | `points.size % 4` | `raise ValueError('CARLA LiDAR buffer is not XYZI float32')` |
| `run` / 171 | `args.frames < 1 or args.media_stride < 1` | `raise ValueError('frames and media-stride must be positive')` |
| `run` / 177 | `args.fixed_delta <= 0.0 or args.sensor_timeout <= 0.0 or args.target_speed_mps < 0.0` | `raise ValueError('fixed-delta and sensor-timeout must be positive; target speed must be non-negative')` |
| `run` / 192 | `_map_leaf(world_map.name).lower() != _map_leaf(args.expected_map).lower()` | `raise RuntimeError(f'current CARLA map is {world_map.name!r}; expected {args.expected_map!r}')` |
| `run` / 198 | `not model_path.is_dir()` | `raise FileNotFoundError(f'Qwen model not found: {model_path}')` |
| `run` / 266 | `trace is None or trace.image_path is None` | `raise RuntimeError('Qwen completed without a trace backed by a real RGB image')` |
| `run` / 313 | `not adapted.control_authorized` | `raise RuntimeError(f'Qwen command rejected by A: {adapted.feedback}')` |
| `run` / 394 | `final_state is None or start_location is None or qwen_report is None` | `raise RuntimeError('closed loop produced no final evidence')` |

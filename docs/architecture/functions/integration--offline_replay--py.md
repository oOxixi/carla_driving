# offline_replay：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/offline_replay.py](../../../integration/offline_replay.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

CARLA-free replay acceptance for recorded RGB/LiDAR/control frames.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ReplayFrameResult.frame: int`；默认：`未在声明处设置`。
- `ReplayFrameResult.qwen_status: str`；默认：`未在声明处设置`。
- `ReplayFrameResult.qwen_error: str | None`；默认：`未在声明处设置`。
- `ReplayFrameResult.watchdog_alerts: tuple[str, ...]`；默认：`未在声明处设置`。
- `ReplayFrameResult.rgb_loaded: bool`；默认：`未在声明处设置`。
- `ReplayFrameResult.lidar_loaded: bool`；默认：`未在声明处设置`。
- `ReplayFrameResult.detection_count: int`；默认：`未在声明处设置`。
- `ReplayFrameResult.lead_distance_m: float | None`；默认：`未在声明处设置`。
- `ReplayFrameResult.safety_override: bool`；默认：`未在声明处设置`。
- `ReplayFrameResult.safety_reason: str`；默认：`未在声明处设置`。
- `ReplayFrameResult.throttle: float`；默认：`未在声明处设置`。
- `ReplayFrameResult.brake: float`；默认：`未在声明处设置`。
- `ReplayFrameResult.steer: float`；默认：`未在声明处设置`。
- `ReplayFrameResult.passed: bool`；默认：`未在声明处设置`。
- `ReplayFrameResult.failures: tuple[str, ...]`；默认：`未在声明处设置`。
- `ReplayReport.manifest: str`；默认：`未在声明处设置`。
- `ReplayReport.frame_count: int`；默认：`未在声明处设置`。
- `ReplayReport.passed_frames: int`；默认：`未在声明处设置`。
- `ReplayReport.failed_frames: int`；默认：`未在声明处设置`。
- `ReplayReport.passed: bool`；默认：`未在声明处设置`。
- `ReplayReport.results: tuple[ReplayFrameResult, ...]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-replayframeresult"></a>

### `ReplayFrameResult`

源码位置：[integration/offline_replay.py 第 43 行](../../../integration/offline_replay.py#L43)。类型：`ClassDef`。

冻结的逐帧回放结果，包含Qwen状态/错误、传感资产是否加载、目标数量/距离、安全覆盖与最终控制、passed/failures。passed只代表本帧声明expected均满足，不等于真实传感/模型/CARLA通过。

<a id="fn-replayreport"></a>

### `ReplayReport`

源码位置：[integration/offline_replay.py 第 62 行](../../../integration/offline_replay.py#L62)。类型：`ClassDef`。

冻结汇总：manifest绝对路径、总/成功/失败帧数、overall passed和逐帧结果；由run_replay_manifest串行复用同一ControlRuntime产生，保留跨帧状态。

<a id="fn-replayreport-to-payload"></a>

### `ReplayReport.to_payload`

源码位置：[integration/offline_replay.py 第 70 行](../../../integration/offline_replay.py#L70)。类型：`FunctionDef`。

```python
ReplayReport.to_payload(self) -> dict[str, Any]
```

加入schema_version=1.0，将results逐项asdict后组成可JSON序列化dict；不写磁盘，tuple由后续json.dumps编码为数组。

<a id="fn-load-replay-manifest"></a>

### `load_replay_manifest`

源码位置：[integration/offline_replay.py 第 82 行](../../../integration/offline_replay.py#L82)。类型：`FunctionDef`。

```python
load_replay_manifest(path: str | Path) -> tuple[dict[str, Any], ...]
```

Read strict JSONL records and enforce increasing aligned frame time.

<a id="fn-run-replay-manifest"></a>

### `run_replay_manifest`

源码位置：[integration/offline_replay.py 第 119 行](../../../integration/offline_replay.py#L119)。类型：`FunctionDef`。

```python
run_replay_manifest(manifest_path: str | Path, *, detector: OnnxYoloDetector | None=None) -> ReplayReport
```

Run recorded frames through perception, Qwen boundary and A/B/C/D.

<a id="fn--run-frame"></a>

### `_run_frame`

源码位置：[integration/offline_replay.py 第 144 行](../../../integration/offline_replay.py#L144)。类型：`FunctionDef`。

```python
_run_frame(payload: Mapping[str, Any], dataset_root: Path, runtime: ControlRuntime, *, detector: OnnxYoloDetector | None) -> ReplayFrameResult
```

验证vehicle/perception键，加载可选RGB/LiDAR；有detector时重算RGB检测覆盖记录值，LiDAR重算前距且缺前速时补0并保留审计语义。可选录制Qwen响应经边界校验/Adapter授权，缺响应PENDING、非法ERROR并fail_closed。随后以dt_s默认0.05且>=1e-6执行runtime.step，比较expected，返回实际最终控制；不调用远端模型。

<a id="fn--evaluate-expected"></a>

### `_evaluate_expected`

源码位置：[integration/offline_replay.py 第 277 行](../../../integration/offline_replay.py#L277)。类型：`FunctionDef`。

```python
_evaluate_expected(raw_expected: object, *, qwen_status: str, rgb_loaded: bool, lidar_loaded: bool, scene: PerceptionFrame, control: Any) -> list[str]
```

只允许_EXPECTED_FIELDS；状态/布尔等做精确比较，brake下限/throttle上限/检测数下限/lead距离闭区间作数值检查。返回失败字符串list；未知键或非法数值直接抛异常，不统一包装成failed。expected={}时没有断言，空失败列表不能说明完整功能正确。

<a id="fn--evaluate-expected-equality"></a>

### `_evaluate_expected.equality`

源码位置：[integration/offline_replay.py 第 292 行](../../../integration/offline_replay.py#L292)。类型：`FunctionDef`。

```python
_evaluate_expected.equality(name: str, actual: object) -> None
```

闭包读取expected，只在name已声明且actual!=expected[name]时追加带期望/实际值的失败文本；未声明的条件不检查。

<a id="fn--vehicle"></a>

### `_vehicle`

源码位置：[integration/offline_replay.py 第 329 行](../../../integration/offline_replay.py#L329)。类型：`FunctionDef`。

```python
_vehicle(raw: object, frame: int, sim_time_s: float) -> RuntimeVehicleState
```

vehicle必须mapping且键集合恰为speed_mps/x_m/y_m/z_m/yaw_deg/lane_id，不允许额外或缺失键；frame和sim_time_s由顶层注入。将值交RuntimeVehicleState，本函数不逐个数值校验所有vehicle字段。

<a id="fn--route"></a>

### `_route`

源码位置：[integration/offline_replay.py 第 340 行](../../../integration/offline_replay.py#L340)。类型：`FunctionDef`。

```python
_route(raw: object, vehicle: RuntimeVehicleState) -> RouteReference
```

raw=None生成从当前位置到世界x+30m的两点直线，并非沿vehicle.yaw方向。显式route_points须list、至少两组[x,y]、每坐标有限；构造curvature=0、target_speed=5m/s的RouteReference。

<a id="fn--detections"></a>

### `_detections`

源码位置：[integration/offline_replay.py 第 359 行](../../../integration/offline_replay.py#L359)。类型：`FunctionDef`。

```python
_detections(raw: object) -> tuple[DetectedObject, ...]
```

None或空tuple返回空tuple；其余必须list，各对象为mapping，必读class_id/class_name/confidence/bbox并转bbox为tuple，distance可空。当前没有把记录中的track_id传给DetectedObject，不能据此验证原追踪身份。

<a id="fn--load-rgb"></a>

### `_load_rgb`

源码位置：[integration/offline_replay.py 第 376 行](../../../integration/offline_replay.py#L376)。类型：`FunctionDef`。

```python
_load_rgb(path: Path) -> np.ndarray
```

npy以allow_pickle=False加载；其他文件需Pillow并convert RGB。最终严格要求uint8且shape(H,W,3)，否则ValueError；不调整图像尺寸。

<a id="fn--load-lidar"></a>

### `_load_lidar`

源码位置：[integration/offline_replay.py 第 391 行](../../../integration/offline_replay.py#L391)。类型：`FunctionDef`。

```python
_load_lidar(payload: Mapping[str, Any], dataset_root: Path) -> np.ndarray
```

lidar_path优先（必须.npy且受dataset路径检查），否则取lidar_points转float32。要求(N,3)或(N,4)且全有限；npy禁pickle，不自动估计目标速度。

<a id="fn--dataset-path"></a>

### `_dataset_path`

源码位置：[integration/offline_replay.py 第 407 行](../../../integration/offline_replay.py#L407)。类型：`FunctionDef`。

```python
_dataset_path(root: Path, raw: object, name: str) -> Path
```

raw必须非空str，合并root后resolve，要求仍在root.resolve之内且is_file；逃逸ValueError、缺文件FileNotFoundError。虽然报错文字称relative path，实现也可能接受解析后仍位于root内的绝对路径。

<a id="fn--mapping"></a>

### `_mapping`

源码位置：[integration/offline_replay.py 第 420 行](../../../integration/offline_replay.py#L420)。类型：`FunctionDef`。

```python
_mapping(value: object, name: str) -> dict[str, Any]
```

仅接受collections.abc.Mapping并返回浅拷贝dict；嵌套对象仍共享，不做JSON深拷贝或字段校验。

<a id="fn--integer"></a>

### `_integer`

源码位置：[integration/offline_replay.py 第 426 行](../../../integration/offline_replay.py#L426)。类型：`FunctionDef`。

```python
_integer(value: object, name: str, *, minimum: int) -> int
```

仅type(value) is int且>=minimum，bool不接受；否则ValueError。用于帧号、最少检测数等整数字段。

<a id="fn--number"></a>

### `_number`

源码位置：[integration/offline_replay.py 第 432 行](../../../integration/offline_replay.py#L432)。类型：`FunctionDef`。

```python
_number(value: object, name: str, *, minimum: float | None=None) -> float
```

仅int/float且非bool，转换float并要求有限；提供minimum时还需>=minimum。类型错误TypeError，非有限或越界ValueError；minimum=None允许负数（例如坐标）。

<a id="fn-write-replay-report"></a>

### `write_replay_report`

源码位置：[integration/offline_replay.py 第 446 行](../../../integration/offline_replay.py#L446)。类型：`FunctionDef`。

```python
write_replay_report(report: ReplayReport, path: str | Path) -> None
```

创建目标父目录（parents=True/exist_ok=True），UTF-8 indent=2写to_payload并加末尾换行。直接覆盖文件而非原子replace，写入异常向上传播。

## 内部调用与异常路径

- `load_replay_manifest` 调用：`Path`, `Path(path).resolve`, `TypeError`, `ValueError`, `_integer`, `_number`, `enumerate`, `json.loads`, `line.startswith`, `manifest.open`, `payload.get`, `raw_line.strip`, `records.append`, `tuple`, `type`.
- `run_replay_manifest` 调用：`ControlRuntime`, `Path`, `Path(manifest_path).resolve`, `PurePursuitController`, `ReplayReport`, `_run_frame`, `len`, `load_replay_manifest`, `results.append`, `str`, `sum`, `tuple`.
- `_run_frame` 调用：`HighLevelCommandAdapter`, `HighLevelCommandAdapter().adapt`, `PerceptionFrame`, `QwenInputContext`, `ReplayFrameResult`, `SimpleNamespace`, `TypeError`, `ValueError`, `_dataset_path`, `_detections`, `_evaluate_expected`, `_integer`, `_load_lidar`, `_load_rgb`, `_mapping`, `_number`, `_route`, `_vehicle`, `asdict`, `build_high_level_command`, `context.to_payload`, `detector.detect_rgb`, `envelope.get`, `fail_closed`, `front_lidar_distance_m`, `len`, `payload.get`, `perception_data.get`, `perception_data.pop`, `qwen_data.get`, `runtime.step`, `runtime.submit_voice`, `safety_vehicle_state`, `set`, `sorted`, `str`, `tuple`, `type`, `validate_qwen_response`.
- `_evaluate_expected` 调用：`ValueError`, `_integer`, `_mapping`, `_number`, `equality`, `failures.append`, `len`, `set`, `sorted`, `type`.
- `_vehicle` 调用：`RuntimeVehicleState`, `ValueError`, `_mapping`, `set`, `sorted`.
- `_route` 调用：`RouteReference`, `ValueError`, `_number`, `len`, `tuple`, `type`.
- `_detections` 调用：`DetectedObject`, `TypeError`, `_mapping`, `item.get`, `tuple`, `type`.
- `_load_rgb` 调用：`Image.open`, `Image.open(path).convert`, `RuntimeError`, `ValueError`, `np.asarray`, `np.load`, `path.suffix.lower`.
- `_load_lidar` 调用：`ValueError`, `_dataset_path`, `np.asarray`, `np.isfinite`, `np.isfinite(points).all`, `np.load`, `path.suffix.lower`, `payload.get`.
- `_dataset_path` 调用：`(root / raw).resolve`, `FileNotFoundError`, `ValueError`, `candidate.is_file`, `candidate.relative_to`, `raw.strip`, `root.resolve`, `type`.
- `_mapping` 调用：`TypeError`, `dict`, `isinstance`.
- `_integer` 调用：`ValueError`, `type`.
- `_number` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `write_replay_report` 调用：`Path`, `destination.parent.mkdir`, `destination.write_text`, `json.dumps`, `report.to_payload`.
- `to_payload` 调用：`asdict`.
- `equality` 调用：`failures.append`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_dataset_path`，第 409 行：`ValueError(f'{name} must be a non-empty relative path')`。
- `_dataset_path`，第 414 行：`ValueError(f'{name} must stay inside the dataset directory')`。
- `_dataset_path`，第 416 行：`FileNotFoundError(f'{name} does not exist: {candidate}')`。
- `_detections`，第 363 行：`TypeError('perception.detected_objects must be a list')`。
- `_evaluate_expected`，第 289 行：`ValueError(f'unknown expected fields: {sorted(unknown)}')`。
- `_integer`，第 428 行：`ValueError(f'{name} must be an integer >= {minimum}')`。
- `_load_lidar`，第 395 行：`ValueError('lidar_path must point to a .npy file')`。
- `_load_lidar`，第 401 行：`ValueError('replay LiDAR must have shape (N, 3) or (N, 4)')`。
- `_load_lidar`，第 403 行：`ValueError('replay LiDAR points must be finite')`。
- `_load_rgb`，第 383 行：`RuntimeError('Pillow is required to replay PNG/JPEG RGB')`。
- `_load_rgb`，第 387 行：`ValueError('replay RGB must be a uint8 array with shape (H, W, 3)')`。
- `_mapping`，第 422 行：`TypeError(f'{name} must be a mapping')`。
- `_number`，第 439 行：`TypeError(f'{name} must be numeric')`。
- `_number`，第 442 行：`ValueError(f'{name} must be finite and >= {minimum}')`。
- `_route`，第 345 行：`ValueError('route_points must contain at least two [x, y] points')`。
- `_route`，第 355 行：`ValueError('each route point must be [x, y]')`。
- `_run_frame`，第 157 行：`ValueError(f'unknown perception fields: {sorted(unknown_perception)}')`。
- `_run_frame`，第 194 行：`TypeError('qwen.voice_command must be a string')`。
- `_run_frame`，第 230 行：`ValueError('validated Qwen decision failed A boundary')`。
- `_run_frame`，第 233 行：`ValueError('Qwen command was not authorized by runtime')`。
- `_vehicle`，第 333 行：`ValueError(f'vehicle fields mismatch; missing={sorted(expected - set(data))}, unknown={sorted(set(data) - expected)}')`。
- `load_replay_manifest`，第 96 行：`ValueError(f'{manifest}:{line_number}: invalid JSON')`。
- `load_replay_manifest`，第 100 行：`TypeError(f'{manifest}:{line_number}: record must be an object')`。
- `load_replay_manifest`，第 102 行：`ValueError(f'{manifest}:{line_number}: unsupported schema_version')`。
- `load_replay_manifest`，第 108 行：`ValueError(f'{manifest}:{line_number}: frame and sim_time_s must increase')`。
- `load_replay_manifest`，第 115 行：`ValueError('replay manifest contains no frame records')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py)
- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [integration/carla_perception.py](../../../integration/carla_perception.py)
- [integration/contracts.py](../../../integration/contracts.py)
- [integration/perception_bridge.py](../../../integration/perception_bridge.py)
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_command_adapter.py](../../../integration/qwen_command_adapter.py)
- [integration/rgb_detector.py](../../../integration/rgb_detector.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)

静态 import 消费者（含测试）：

- [integration/__init__.py](../../../integration/__init__.py)
- [integration/tests/test_offline_replay.py](../../../integration/tests/test_offline_replay.py)
- [tools/replay_acceptance.py](../../../tools/replay_acceptance.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-offline-replay-py"></a>

### `integration/offline_replay.py`

来源 SHA256：`84cc29af18c9cd9c03978596fbf13ae26dae43cca8a3ad565aef7b5ee565d1a2`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ReplayFrameResult.frame` | `int` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.qwen_status` | `str` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.qwen_error` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.watchdog_alerts` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.rgb_loaded` | `bool` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.lidar_loaded` | `bool` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.detection_count` | `int` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.lead_distance_m` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.safety_override` | `bool` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.safety_reason` | `str` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.throttle` | `float` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.brake` | `float` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.steer` | `float` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.passed` | `bool` | `无声明默认；构造/赋值方提供` |
| `ReplayFrameResult.failures` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `ReplayReport.manifest` | `str` | `无声明默认；构造/赋值方提供` |
| `ReplayReport.frame_count` | `int` | `无声明默认；构造/赋值方提供` |
| `ReplayReport.passed_frames` | `int` | `无声明默认；构造/赋值方提供` |
| `ReplayReport.failed_frames` | `int` | `无声明默认；构造/赋值方提供` |
| `ReplayReport.passed` | `bool` | `无声明默认；构造/赋值方提供` |
| `ReplayReport.results` | `tuple[ReplayFrameResult, ...]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `load_replay_manifest` / 96 | `except json.JSONDecodeError` | `raise ValueError(f'{manifest}:{line_number}: invalid JSON') from error` |
| `load_replay_manifest` / 100 | `type(payload) is not dict` | `raise TypeError(f'{manifest}:{line_number}: record must be an object')` |
| `load_replay_manifest` / 102 | `payload.get('schema_version') != REPLAY_SCHEMA_VERSION` | `raise ValueError(f'{manifest}:{line_number}: unsupported schema_version')` |
| `load_replay_manifest` / 108 | `frame <= previous_frame or sim_time <= previous_time` | `raise ValueError(f'{manifest}:{line_number}: frame and sim_time_s must increase')` |
| `load_replay_manifest` / 115 | `not records` | `raise ValueError('replay manifest contains no frame records')` |
| `_run_frame` / 157 | `unknown_perception` | `raise ValueError(f'unknown perception fields: {sorted(unknown_perception)}')` |
| `_run_frame` / 194 | `qwen is not None AND type(voice) is not str` | `raise TypeError('qwen.voice_command must be a string')` |
| `_run_frame` / 230 | `qwen is not None AND NOT ('response' not in qwen_data) AND envelope.get('status') != 'valid'` | `raise ValueError('validated Qwen decision failed A boundary')` |
| `_run_frame` / 233 | `qwen is not None AND NOT ('response' not in qwen_data) AND not adapted.control_authorized` | `raise ValueError('Qwen command was not authorized by runtime')` |
| `_evaluate_expected` / 289 | `unknown` | `raise ValueError(f'unknown expected fields: {sorted(unknown)}')` |
| `_vehicle` / 333 | `set(data) != expected` | `raise ValueError(f'vehicle fields mismatch; missing={sorted(expected - set(data))}, unknown={sorted(set(data) - expected)}')` |
| `_route` / 345 | `NOT (raw is None) AND type(raw) is not list or len(raw) < 2` | `raise ValueError('route_points must contain at least two [x, y] points')` |
| `_route` / 355 | `NOT (raw is None) AND len(points) != len(raw)` | `raise ValueError('each route point must be [x, y]')` |
| `_detections` / 363 | `type(raw) is not list` | `raise TypeError('perception.detected_objects must be a list')` |
| `_load_rgb` / 383 | `NOT (path.suffix.lower() == '.npy') AND except ImportError` | `raise RuntimeError('Pillow is required to replay PNG/JPEG RGB') from error` |
| `_load_rgb` / 387 | `image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8` | `raise ValueError('replay RGB must be a uint8 array with shape (H, W, 3)')` |
| `_load_lidar` / 395 | `payload.get('lidar_path') is not None AND path.suffix.lower() != '.npy'` | `raise ValueError('lidar_path must point to a .npy file')` |
| `_load_lidar` / 401 | `points.ndim != 2 or points.shape[1] not in {3, 4}` | `raise ValueError('replay LiDAR must have shape (N, 3) or (N, 4)')` |
| `_load_lidar` / 403 | `not np.isfinite(points).all()` | `raise ValueError('replay LiDAR points must be finite')` |
| `_dataset_path` / 409 | `type(raw) is not str or not raw.strip()` | `raise ValueError(f'{name} must be a non-empty relative path')` |
| `_dataset_path` / 414 | `except ValueError` | `raise ValueError(f'{name} must stay inside the dataset directory') from error` |
| `_dataset_path` / 416 | `not candidate.is_file()` | `raise FileNotFoundError(f'{name} does not exist: {candidate}')` |
| `_mapping` / 422 | `not isinstance(value, Mapping)` | `raise TypeError(f'{name} must be a mapping')` |
| `_integer` / 428 | `type(value) is not int or value < minimum` | `raise ValueError(f'{name} must be an integer >= {minimum}')` |
| `_number` / 439 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be numeric')` |
| `_number` / 442 | `not math.isfinite(result) or (minimum is not None and result < minimum)` | `raise ValueError(f'{name} must be finite and >= {minimum}')` |

### integration/offline_replay.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 152 | `_number(payload.get('sim_time_s'), 'sim_time_s', minimum=0.0)` |
| 242 | `_number(payload.get('dt_s', 0.05), 'dt_s', minimum=1e-06)` |
| 106 | `_number(payload.get('sim_time_s'), 'sim_time_s', minimum=0.0)` |
| 301 | `_number(expected['min_brake'], 'expected.min_brake', minimum=0.0)` |
| 305 | `_number(expected['max_throttle'], 'expected.max_throttle', minimum=0.0)` |
| 322 | `_number(bounds[0], 'lead_distance_range_m[0]', minimum=0.0)` |
| 323 | `_number(bounds[1], 'lead_distance_range_m[1]', minimum=minimum)` |
| 348 | `_number(item[0], 'route x')` |
| 349 | `_number(item[1], 'route y')` |

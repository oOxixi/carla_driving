# Sensor acquisition, detection and source audit

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [同帧感知、目标身份与来源](../functions/perception-authority.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

Live chain: CarlaPerceptionBridge.acquire -> PerceptionFrame -> C/D. RGB/LiDAR require aligned frames; Radar is optional with a bounded wait. OnnxYoloDetector supplies optional RGB detections and SensorObjectTracker preserves IDs. The perception package separately provides SensorSynchronizer/RGBPipeline/FusionTracker and canonical PerceptionState. audit_control_sources classifies SENSOR/MAP/ORACLE/SYNTHETIC/DERIVED/UNKNOWN; strict sensor mode flags truth/synthetic control inputs. canonical_bridge currently estimates y from image center, substitutes 50 m for missing distance, and zero speed for non-first objects. These are approximations, not measured fusion truth.


## 模块接口与参数核对（2026-09-20）

CarlaPerceptionBridge.acquire生成PerceptionSample，其中frame为PerceptionFrame、sensor_ready_ns用于时序、source_by_field用于来源审计、rgb/lidar/radar用于证据/模型。PerceptionFrame可选距离/速度为空；UNKNOWN灯态不能写成GREEN。

### 参数语义与生效边界

DetectedObject的bbox_xyxy_norm是归一化框；distance_m与track_id可缺失。RGB/LiDAR要求对齐，Radar为可选且有等待边界。TemporalLeadTracker的hold_s=0.75属于该追踪器默认，不代表所有传感器统一允许750ms延迟。

### 上下游与修改影响

当前canonical桥存在缺距离50m替代、横向位置估算等近似，应保留来源而非宣称真值测量。修改目标ID/排序需联动request、Student pointer、Teacher target和evidence aliases；控制来源审计不应被oracle目标覆盖。

### [integration/contracts.py](../../../integration/contracts.py) 的入口与声明


类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `DetectedObject.class_id` | `int` | `无声明默认（构造/赋值方提供）` |
| `DetectedObject.class_name` | `str` | `无声明默认（构造/赋值方提供）` |
| `DetectedObject.confidence` | `float` | `无声明默认（构造/赋值方提供）` |
| `DetectedObject.bbox_xyxy_norm` | `tuple[float, float, float, float]` | `无声明默认（构造/赋值方提供）` |
| `DetectedObject.distance_m` | `float &#124; None` | `None` |
| `DetectedObject.track_id` | `str &#124; None` | `None` |
| `PerceptionFrame.frame` | `int` | `无声明默认（构造/赋值方提供）` |
| `PerceptionFrame.sim_time_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerceptionFrame.lead_distance_m` | `float &#124; None` | `None` |
| `PerceptionFrame.lead_speed_mps` | `float &#124; None` | `None` |
| `PerceptionFrame.traffic_light` | `str` | `'UNKNOWN'` |
| `PerceptionFrame.distance_to_stop_line_m` | `float &#124; None` | `None` |
| `PerceptionFrame.speed_limit_mps` | `float &#124; None` | `None` |
| `PerceptionFrame.lane_offset_m` | `float &#124; None` | `None` |
| `PerceptionFrame.route_deviation_m` | `float &#124; None` | `None` |
| `PerceptionFrame.collision` | `bool` | `False` |
| `PerceptionFrame.red_light_violation` | `bool` | `False` |
| `PerceptionFrame.lane_invasion` | `bool` | `False` |
| `PerceptionFrame.detected_objects` | `tuple[DetectedObject, ...]` | `()` |
| `FrameResult.vehicle` | `RuntimeVehicleState` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.final_control` | `ControlOutput` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.longitudinal` | `LongitudinalOutput &#124; None` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.safety_reason` | `str` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.safety_override` | `bool` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.feedback` | `tuple[ExecutionFeedback, ...]` | `()` |
| `FrameResult.raw_control` | `Any &#124; None` | `None` |
| `FrameResult.lateral` | `LateralOutput &#124; None` | `None` |
| `FrameResult.safety_reason_category` | `str` | `'NONE'` |

### [integration/carla_perception.py](../../../integration/carla_perception.py) 的入口与声明

```python
sensor_specs_for_profile(profile: str) -> tuple[CarlaSensorSpec, ...]
EventLedger.__init__(self, *, retain_frames: int=64) -> None
EventLedger.collision_callback(self, event: Any) -> None
EventLedger.lane_invasion_callback(self, event: Any) -> None
EventLedger.flags_for_frame(self, frame: int) -> tuple[bool, bool]
attach_default_sensors(session: CarlaSession, world: Any, ego: Any, carla_api: Any, *, specs: Sequence[CarlaSensorSpec]=DEFAULT_SENSOR_SPECS, sensor_tick_s: float | None=None) -> AttachedCarlaSensors
attach_event_sensors(session: CarlaSession, world: Any, ego: Any, carla_api: Any) -> AttachedCarlaSensors
front_lidar_distance_m(measurement: Any, *, min_range_m: float=1.0, max_range_m: float=60.0, half_width_m: float=1.35, min_height_m: float=-1.8, max_height_m: float=-0.7, minimum_points: int=3) -> float | None
adjacent_lidar_distances_m(measurement: Any, *, min_forward_m: float=1.0, max_forward_m: float=25.0, inner_lateral_m: float=1.75, outer_lateral_m: float=5.25, min_height_m: float=-1.8, max_height_m: float=-0.7, minimum_points: int=3) -> tuple[float | None, float | None]
TemporalLeadTracker.reset(self) -> None
TemporalLeadTracker.update(self, *, sim_time_s: float, ego_speed_mps: float, observed_distance_m: float | None, observed_lead_speed_mps: float | None) -> tuple[float | None, float | None, bool]
front_radar_target(measurement: Any, *, sensor_x_offset_m: float=1.5, min_range_m: float=1.0, max_range_m: float=80.0, half_width_m: float=1.75, min_altitude_deg: float=-3.0, max_altitude_deg: float=3.0) -> FrontRadarTarget | None
traffic_light_and_stop_distance(ego: Any, traffic_lights: Iterable[Any]=(), *, world_map: Any | None=None) -> tuple[str, float | None, str]
actor_speed_limit_mps(ego: Any) -> float | None
route_deviation_m(x_m: float, y_m: float, route: RouteReference) -> float
lane_metrics(world_map: Any, ego: Any, route: RouteReference | None) -> tuple[float | None, float | None]
CarlaPerceptionBridge.__init__(self, world: Any, world_map: Any, ego: Any, session: CarlaSession, sensors: AttachedCarlaSensors, detector: Any | None=None, *, visual_provider: Callable[[Any], VisualObservation] | None=None, fusion: ConservativeSensorFusion | None=None) -> None
CarlaPerceptionBridge.acquire(self, frame: int, sim_time_s: float, *, route: RouteReference | None=None, timeout_s: float=0.25) -> PerceptionSample
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `SensorMount.x_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SensorMount.y_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SensorMount.z_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `SensorMount.pitch_deg` | `float` | `0.0` |
| `SensorMount.yaw_deg` | `float` | `0.0` |
| `SensorMount.roll_deg` | `float` | `0.0` |
| `CarlaSensorSpec.sensor_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `CarlaSensorSpec.blueprint_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `CarlaSensorSpec.mount` | `SensorMount` | `无声明默认（构造/赋值方提供）` |
| `CarlaSensorSpec.attributes` | `Mapping[str, str]` | `field(default_factory=dict)` |
| `CarlaSensorSpec.continuous` | `bool` | `True` |
| `AttachedCarlaSensors.actors` | `Mapping[str, Any]` | `无声明默认（构造/赋值方提供）` |
| `AttachedCarlaSensors.events` | `EventLedger` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSample.frame` | `PerceptionFrame` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSample.sensor_ready_ns` | `int` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSample.source_by_field` | `Mapping[str, str]` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSample.rgb` | `Any` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSample.lidar` | `Any` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSample.radar` | `Any &#124; None` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSample.safety_summary` | `SafetyStateSummary` | `无声明默认（构造/赋值方提供）` |
| `PerceptionSample.multi_view_rgb` | `Mapping[str, Any]` | `field(default_factory=dict)` |
| `FrontRadarTarget.distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `FrontRadarTarget.closing_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `TemporalLeadTracker.hold_s` | `float` | `0.75` |
| `TemporalLeadTracker.acquire_within_m` | `float` | `35.0` |
| `TemporalLeadTracker.max_lead_speed_mps` | `float` | `20.0` |
| `TemporalLeadTracker.distance_m` | `float &#124; None` | `None` |
| `TemporalLeadTracker.lead_speed_mps` | `float &#124; None` | `None` |
| `TemporalLeadTracker.last_update_s` | `float &#124; None` | `None` |
| `TemporalLeadTracker.last_observed_s` | `float &#124; None` | `None` |
| `TemporalLeadTracker.last_observed_distance_m` | `float &#124; None` | `None` |
| `TemporalLeadTracker.ego_travel_since_observation_m` | `float` | `0.0` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [integration/carla_perception.py](../../../integration/carla_perception.py) - `PerceptionAcquisitionError`, `PerceptionTimeoutError`, `FrameAlignmentError`, `PerceptionDataError`, `ObjectDetectionError`, `SensorMount`, `CarlaSensorSpec`, `sensor_specs_for_profile`, `EventLedger`, `EventLedger.collision_callback`, `EventLedger.lane_invasion_callback`, `EventLedger.flags_for_frame`, `AttachedCarlaSensors`, `PerceptionSample`, `_make_transform`, `_configured_blueprint`, `attach_default_sensors`, `attach_event_sensors`, `_xyz`, `_speed_mps`, `_lidar_xyz`, `front_lidar_distance_m`, `adjacent_lidar_distances_m`, `FrontRadarTarget`, `TemporalLeadTracker`, `TemporalLeadTracker.reset`, `TemporalLeadTracker.update`, `front_radar_target`, `_normalise_light_state`, `_upcoming_traffic_light`, `traffic_light_and_stop_distance`, `actor_speed_limit_mps`, `route_deviation_m`, `lane_metrics`, `CarlaPerceptionBridge`, `CarlaPerceptionBridge.acquire`
- [integration/contracts.py](../../../integration/contracts.py) - `_finite_or_none`, `DetectedObject`, `PerceptionFrame`, `FrameResult`
- [integration/object_tracker.py](../../../integration/object_tracker.py) - `_center`, `_Track`, `SensorObjectTracker`, `SensorObjectTracker.update`
- [integration/perception_bridge.py](../../../integration/perception_bridge.py) - `longitudinal_request`, `safety_vehicle_state`
- [integration/perception_stage.py](../../../integration/perception_stage.py) - `ObservationAuthority`, `classify_observation_source`, `PerceptionSourceAudit`, `PerceptionSourceAudit.control_clean`, `PerceptionSourceAudit.to_dict`, `audit_control_sources`
- [integration/rgb_detector.py](../../../integration/rgb_detector.py) - `OnnxDetectionError`, `_Letterbox`, `carla_rgb_array`, `_resize_rgb`, `_letterbox`, `_box_iou`, `_class_aware_nms`, `OnnxYoloDetector`, `OnnxYoloDetector.detect_measurement`, `OnnxYoloDetector.detect_rgb`, `driving_corridor_detections`
- [perception/__init__.py](../../../perception/__init__.py) - module/resource/documentation
- [perception/fault_injection.py](../../../perception/fault_injection.py) - `inject_sensor_fault`, `inject_observation_fault`, `main`
- [perception/fault_injection.sh](../../../perception/fault_injection.sh) - module/resource/documentation
- [perception/fusion_tracker.py](../../../perception/fusion_tracker.py) - `Observation`, `FusedObject`, `FusionTrackerConfig`, `FusionResult`, `_TrackState`, `FusionTracker`, `FusionTracker.update`
- [perception/perception_state.json](../../../perception/perception_state.json) - module/resource/documentation
- [perception/README.md](../../../perception/README.md) - module/resource/documentation
- [perception/rgb_pipeline.py](../../../perception/rgb_pipeline.py) - `RGBPipelineConfig`, `RGBDetection`, `RGBTrack`, `_iou`, `RGBPipeline`, `RGBPipeline.process`, `RGBPipeline.metrics`
- [perception/sensor_adapter.py](../../../perception/sensor_adapter.py) - `Modality`, `_finite`, `Extrinsics`, `Extrinsics.transform_point`, `Extrinsics.rotate_vector`, `Extrinsics.to_dict`, `SensorSample`, `SensorSample.invalidated`, `AlignedSensorFrame`, `AlignedSensorFrame.sample`, `SensorSynchronizer`, `SensorSynchronizer.push`, `SensorSynchronizer.align`, `SensorRecorder`, `SensorRecorder.record`, `SensorRecorder.close`, `SensorReplayer`

## Dependencies and coordinated changes

## 第6模块逐项精读结论（2026-09-21）

本轮核对12份感知实现页，其中10页的96处通用占位已经按当前函数体替换；另外两页是包导出和 shell 入口，本来没有函数占位。精读覆盖真实 CARLA 采集链、二维检测/追踪、来源审计，以及独立 `perception/` 参考管线；不把离线接口回归等同于真实摄像头/LiDAR/Radar质量验收。

### 生产感知链

1. runner 根据 sensor profile 附着传感器；`default` 是800×450前视RGB、32线224k点/s LiDAR、3k点/s Radar及两个事件传感器，`low` 降分辨率/点密度，`competition_multiview` 再增加左/右/后RGB。连续传感器进入 frame buffer，碰撞和压线进入独立 `EventLedger`。
2. `CarlaPerceptionBridge.acquire(frame, sim_time)` 对前RGB、LiDAR和已配置多视角RGB作必需同帧等待；Radar是可选同帧输入，只等待最多5 ms grace。必需输入超时、payload帧不符、LiDAR不可解析或已配置检测器失败均抛 `PerceptionAcquisitionError` 子类，runner抑制普通控制并走启动宽限或watchdog安全路径。
3. LiDAR前走廊要求1–60 m、横向±1.35 m、高度−1.8至−0.7 m且至少3点，取前向距离10百分位；相邻车道在左右1.75–5.25 m带内按xy距离取10百分位。高度门限刻意排除树冠、灯臂和高架等头顶回波。
4. Radar候选按深度/方位/高度换算到ego前向距离，选择走廊内最近有限目标。Radar与LiDAR相差不超过4 m才给现有前车补速度；没有LiDAR时仅8 m内Radar触发控制侧短距兜底，远距孤立Radar只作为Qwen候选，不进入 `lead_distance_m`。
5. `TemporalLeadTracker` 对35 m内前车最多保持0.75 s：新近的回波总能接管，突然跳到远处的背景回波会被抑制；缺测期按自车与已知前车速度推进距离。一帧不足以估速时保守按前车静止，后续距离差分只在时间窗内且速度为0–20 m/s时采用，并对已有速度作0.65/0.35平滑。
6. RGB检测结果全部保留供Qwen和审计，只有画面中心35%–65%且框底部不低于30%的目标进入前向控制语义。LiDAR前方有目标而RGB漏检时仍构造泛化 `obstacle`；相邻LiDAR目标追加为左右目标。最终由 `SensorObjectTracker` 分配 `C-xxxx` ID。
7. 交通灯优先使用active light和地图停止点，也能在CARLA尚未标记active前按同车道、朝向、前后/横向几何寻找upcoming stop waypoint；trigger volume只作明确标记的近似。限速由km/h除3.6，车道偏移和路线偏差来自地图/路线几何。
8. `PerceptionSample` 同时交付控制 `PerceptionFrame`、原始模态、C融合摘要、`sensor_ready_ns` 和逐字段来源。严格传感器模式随后用 `audit_control_sources` 禁止 ORACLE/SYNTHETIC 来源；UNKNOWN/DERIVED不会被该审计自动拒绝，仍需字段质量门禁。

### 三套容易混淆的目标/融合实现

| 实现 | 当前用途 | ID/同步语义 |
|---|---|---|
| `CarlaPerceptionBridge + SensorObjectTracker` | runner生产CARLA链 | 必需模态精确frame；`C-xxxx`二维类别/中心/距离贪心关联 |
| `ConservativeSensorFusion` | 生产C安全摘要 | LiDAR/RGB同帧、Radar或距离差分速度；输出动作/速度cap，不分配Qwen目标ID |
| `perception.SensorSynchronizer/RGBPipeline/FusionTracker` | benchmark、回放与独立感知交付 | 四模态默认必需、捕获时间容差；`rgb-xxxxxx`和`fused-xxxxxx`属于各自管线 |

`rg` 当前显示独立 `perception/` 三件套的非测试消费者是 `tools/benchmark_perception_pipeline.py`；runner生产链直接实例化 `CarlaPerceptionBridge`。因此独立管线测试通过不能证明runner已经使用其四模态融合，反过来也不能删掉它的回放/交付用途。

### Canonical/Qwen转换的近似边界

`perception_frame_to_state` 把 `PerceptionFrame` 转为模型/接口状态时仍有显式近似：无距离目标补50 m，横向位置用 `(0.5-image_center)*7`，没有track ID时用类别+列表索引，只有列表第一个对象获得 `scene.lead_speed_mps`，其他对象速度置0。传感器模式下 obstacle+距离标成LiDAR，语义目标标RGB并可追加LiDAR；非传感器模式统一标WORLD。这些字段满足schema不代表是三维传感器真值。

### 目标身份与来源维护规则

- scenario actor ID、传感器 track ID、Qwen plan target ID 是三层身份；只允许通过同一命令/提交帧的 evidence alias 做验收归因，不能把oracle actor ID塞回感知目标。
- `SensorObjectTracker` 的默认匹配要求同类别、归一化中心L1位移≤0.25；两帧都有距离时还要求距离差不超过 `max(3 m, previous_distance*25%)`。距离缺失不会单独阻止匹配，超过5帧历史淘汰。
- `EventLedger.flags_for_frame(N)` 会消费所有 `<=N` 的迟到事件，使N帧之后才到的事件能在N+1显示；collision/lane invasion是事件事实，不是逐帧持续状态。
- 来源分类使用字符串token包含和固定优先级。新增来源名必须补分类回归，避免包含 `CARLA_TRUTH_` 等token而被意外归为oracle，或未知来源被当作普通DERIVED。

### 已确认边界与保留问题

- **M06-01 / 已复现、未修复：调用者提供的重复track ID不保证同帧唯一。** `SensorObjectTracker.update` 对非空 `detection.track_id` 直接采用；两个输入都带 `dup` 时输出两个 `dup`，内部表又由后一个覆盖前一个。生产 `OnnxYoloDetector` 当前不给ID，因此正常bridge路径主要由tracker分配；但该公开接口和未来上游带ID接入需要唯一性门禁或冲突重命名。
- **M06-02 / 已复现、未修复：canonical目标速度按列表索引而非距离关联。** 两个目标依次为无距离side和10 m lead，`scene.lead_speed_mps=2` 时，转换结果给side写2 m/s和50 m，真正lead写0 m/s和10 m，TTC分别成为6.25 s和1.0 s；这与前车速度应绑定的对象不一致。修复需按range/track关联速度，并联动Qwen排序、Student pointer和历史schema回归。
- `SensorSynchronizer` 默认四模态全部必需且Radar缺失会stale，生产bridge则把Radar设为可选；复用配置时必须明确适用链，不能把一个默认直接覆盖另一个。

### 验证范围

本轮实际执行：

```text
python -m pytest integration/tests/test_carla_perception.py \
  integration/tests/test_role_c_perception.py integration/tests/test_object_tracker.py \
  integration/tests/test_rgb_detector.py integration/tests/test_perception_stage.py \
  integration/tests/test_canonical_bridge.py integration/tests/test_sensor_profiles.py -q
79 passed in 0.91s
```

另外用纯Python调用复现M06-01/M06-02。上述验证不启动CARLA、不加载真实ONNX模型，也未测夜间/雨雾、传感器噪声、目标ID实车稳定性或真实Radar/LiDAR覆盖。


## Validation entry points

`python -m pytest integration/tests/test_carla_perception.py integration/tests/test_role_c_perception.py integration/tests/test_object_tracker.py integration/tests/test_rgb_detector.py integration/tests/test_perception_stage.py integration/tests/test_canonical_bridge.py integration/tests/test_sensor_profiles.py`

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [integration/carla_perception.py](../functions/integration--carla_perception--py.md)
- [integration/contracts.py](../functions/integration--contracts--py.md)
- [integration/object_tracker.py](../functions/integration--object_tracker--py.md)
- [integration/perception_bridge.py](../functions/integration--perception_bridge--py.md)
- [integration/perception_stage.py](../functions/integration--perception_stage--py.md)
- [integration/rgb_detector.py](../functions/integration--rgb_detector--py.md)
- [perception/__init__.py](../functions/perception--__init__--py.md)
- [perception/fault_injection.py](../functions/perception--fault_injection--py.md)
- [perception/fault_injection.sh](../functions/perception--fault_injection--sh.md)
- [perception/fusion_tracker.py](../functions/perception--fusion_tracker--py.md)
- [perception/rgb_pipeline.py](../functions/perception--rgb_pipeline--py.md)
- [perception/sensor_adapter.py](../functions/perception--sensor_adapter--py.md)

## 诊断与维护交接

本模块证据：同帧时间、track ID、来源、request目标；历史关联需实际日志。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

专项记录：[目标身份、空值与验收归因](../functions/target-grounding.md)。

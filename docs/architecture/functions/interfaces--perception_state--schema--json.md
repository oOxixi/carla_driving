# perception_state.schema：功能记录

上级模块：[模块说明](../modules/vehicle-interfaces.md) · 实现：[interfaces/perception_state.schema.json](../../../interfaces/perception_state.schema.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [版本、时间、坐标与适配语义](interface-versioning.md)

## 功能职责与范围

perception_state.schema

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `$schema`：'https://json-schema.org/draft/2020-12/schema'。
- `$id`：'https://carla-driving.local/interfaces/perception_state.schema.json'。
- `title`：'PerceptionState V1'。
- `type`：'object'。
- `additionalProperties`：False。
- `required`：列表，共 13 项。
- `properties`：对象，直接字段：schema_version, frame_id, sim_time_s, captured_at_ns, coordinate_frame, objects, traffic_light, distance_to_stop_line_m, speed_limit_mps, ttc_s, min_gap_m, risk_level, modality_valid, stale, sync, degraded_reason_codes。
- `examples`：列表，共 1 项。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-interfaces.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `interfaces/perception_state.schema.json`

来源 SHA256：`a4cc34630735cffaf25dce28ff9fa929cd48c5421bf28f8369caf94fcda7897b`。


Schema 字段与约束：$ref需解析到对应定义；required只表示本层必填，不能代替分支条件判断。

| 路径 | 必填位置 | 类型/枚举/范围/额外字段策略 |
|---|---|---|
| `$` | 根 | `{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://carla-driving.local/interfaces/perception_state.schema.json", "title": "PerceptionState V1", "type": "object", "additionalProperties": false, "required": ["schema_version", "frame_id", "sim_time_s", "captured_at_ns", "coordinate_frame", "objects", "traffic_light", "ttc_s", "min_gap_m", "risk_level", "modality_valid", "stale", "sync"], "examples": [{"schema_version": "1.0", "frame_id": 120, "sim_time_s": 6.0, "captured_at_ns": 3000000000, "coordinate_frame": "ego_front_x_left_y_up_z_m", "objects": [{"track_id": "vehicle-0001", "class": "vehicle", "position_m": [12.0, -3.5, 0.0], "velocity_mps": [4.0, 0.0, 0.0], "distance_m": 12.5, "ttc_s": null, "confidence": 0.94, "sources": ["RGB", "RADAR", "LIDAR"], "bbox_xyxy_norm": [0.62, 0.4, 0.79, 0.76]}], "traffic_light": "GREEN", "distance_to_stop_line_m": null, "speed_limit_mps": 8.3333333333, "ttc_s": null, "min_gap_m": 12.5, "risk_level": "LOW", "modality_valid": {"rgb": true, "radar": true, "lidar": true, "vehicle_state": true}, "stale": false, "sync": {"reference_frame_id": 120, "max_skew_ms": 18.0, "within_tolerance": true, "missing_modalities": []}, "degraded_reason_codes": []}]}` |
| `$.schema_version` | 是 | `{"const": "1.0"}` |
| `$.frame_id` | 是 | `{"type": "integer", "minimum": 0}` |
| `$.sim_time_s` | 是 | `{"type": "number", "minimum": 0}` |
| `$.captured_at_ns` | 是 | `{"type": "integer", "minimum": 0}` |
| `$.coordinate_frame` | 是 | `{"const": "ego_front_x_left_y_up_z_m"}` |
| `$.objects` | 是 | `{"type": "array", "maxItems": 128}` |
| `$.objects[]` | 数组元素 | `{"type": "object", "additionalProperties": false, "required": ["track_id", "class", "position_m", "velocity_mps", "distance_m", "confidence", "sources"]}` |
| `$.objects[].track_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.objects[].class` | 是 | `{"enum": ["vehicle", "pedestrian", "cyclist", "obstacle", "unknown"]}` |
| `$.objects[].position_m` | 是 | `{"type": "array", "minItems": 3, "maxItems": 3}` |
| `$.objects[].position_m[]` | 数组元素 | `{"type": "number"}` |
| `$.objects[].velocity_mps` | 是 | `{"type": "array", "minItems": 3, "maxItems": 3}` |
| `$.objects[].velocity_mps[]` | 数组元素 | `{"type": "number"}` |
| `$.objects[].distance_m` | 是 | `{"type": "number", "minimum": 0}` |
| `$.objects[].ttc_s` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0}` |
| `$.objects[].confidence` | 是 | `{"type": "number", "minimum": 0, "maximum": 1}` |
| `$.objects[].sources` | 是 | `{"type": "array", "minItems": 1, "uniqueItems": true}` |
| `$.objects[].sources[]` | 数组元素 | `{"enum": ["RGB", "RADAR", "LIDAR", "WORLD"]}` |
| `$.objects[].bbox_xyxy_norm` | 否（不等于允许null） | `{"type": ["array", "null"], "minItems": 4, "maxItems": 4}` |
| `$.objects[].bbox_xyxy_norm[]` | 数组元素 | `{"type": "number", "minimum": 0, "maximum": 1}` |
| `$.traffic_light` | 是 | `{"enum": ["RED", "YELLOW", "GREEN", "UNKNOWN"]}` |
| `$.distance_to_stop_line_m` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0}` |
| `$.speed_limit_mps` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0}` |
| `$.ttc_s` | 是 | `{"type": ["number", "null"], "minimum": 0}` |
| `$.min_gap_m` | 是 | `{"type": ["number", "null"], "minimum": 0}` |
| `$.risk_level` | 是 | `{"enum": ["LOW", "CAUTION", "HIGH", "EMERGENCY", "UNKNOWN"]}` |
| `$.modality_valid` | 是 | `{"type": "object", "additionalProperties": false, "required": ["rgb", "radar", "lidar", "vehicle_state"]}` |
| `$.modality_valid.rgb` | 是 | `{"type": "boolean"}` |
| `$.modality_valid.radar` | 是 | `{"type": "boolean"}` |
| `$.modality_valid.lidar` | 是 | `{"type": "boolean"}` |
| `$.modality_valid.vehicle_state` | 是 | `{"type": "boolean"}` |
| `$.stale` | 是 | `{"type": "boolean"}` |
| `$.sync` | 是 | `{"type": "object", "additionalProperties": false, "required": ["reference_frame_id", "max_skew_ms", "within_tolerance"]}` |
| `$.sync.reference_frame_id` | 是 | `{"type": "integer", "minimum": 0}` |
| `$.sync.max_skew_ms` | 是 | `{"type": "number", "minimum": 0}` |
| `$.sync.within_tolerance` | 是 | `{"type": "boolean"}` |
| `$.sync.missing_modalities` | 否（不等于允许null） | `{"type": "array", "uniqueItems": true}` |
| `$.sync.missing_modalities[]` | 数组元素 | `{"enum": ["RGB", "RADAR", "LIDAR", "VEHICLE_STATE"]}` |
| `$.degraded_reason_codes` | 否（不等于允许null） | `{"type": "array", "uniqueItems": true}` |
| `$.degraded_reason_codes[]` | 数组元素 | `{"type": "string", "minLength": 1, "maxLength": 128}` |

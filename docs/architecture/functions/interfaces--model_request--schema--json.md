# model_request.schema：功能记录

上级模块：[模块说明](../modules/vehicle-interfaces.md) · 实现：[interfaces/model_request.schema.json](../../../interfaces/model_request.schema.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [版本、时间、坐标与适配语义](interface-versioning.md)

## 功能职责与范围

model_request.schema

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `$schema`：'https://json-schema.org/draft/2020-12/schema'。
- `$id`：'https://carla-driving.local/interfaces/model_request.schema.json'。
- `title`：'ModelRequest V1'。
- `type`：'object'。
- `additionalProperties`：False。
- `required`：列表，共 9 项。
- `properties`：对象，直接字段：schema_version, request_id, command_id, created_at_ns, deadline_ns, source_text, command_hint, rgb_ref, routing, scene_capabilities, scene_summary, targets, constraints。
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

### `interfaces/model_request.schema.json`

来源 SHA256：`3ef806ea5bdb15716e5bc0957fd31bdc10780f3c2632e40ea7b1c2c30e0c5b64`。


Schema 字段与约束：$ref需解析到对应定义；required只表示本层必填，不能代替分支条件判断。

| 路径 | 必填位置 | 类型/枚举/范围/额外字段策略 |
|---|---|---|
| `$` | 根 | `{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://carla-driving.local/interfaces/model_request.schema.json", "title": "ModelRequest V1", "type": "object", "additionalProperties": false, "required": ["schema_version", "request_id", "command_id", "created_at_ns", "deadline_ns", "source_text", "scene_summary", "targets", "constraints"], "examples": [{"schema_version": "1.0", "request_id": "qwen-0001", "command_id": "voice-0002", "created_at_ns": 2000000000, "deadline_ns": 2300000000, "source_text": "跟随右侧较近的车辆", "rgb_ref": "frames/rgb_000120.png", "scene_summary": {"frame_id": 120, "sim_time_s": 6.0, "traffic_light": "GREEN", "risk_level": "LOW", "min_gap_m": 12.0, "ttc_s": null}, "targets": [{"target_id": "vehicle-right-01", "class": "vehicle", "distance_m": 12.0, "relative_speed_mps": -1.0, "confidence": 0.94, "relation": "right_adjacent_near"}], "constraints": {"speed_limit_mps": 8.3333333333, "allowed_behaviors": ["KEEP_LANE", "SLOW_DOWN", "STOP", "FOLLOW"], "must_stop": false, "max_target_speed_mps": 8.3333333333}}]}` |
| `$.schema_version` | 是 | `{"const": "1.0"}` |
| `$.request_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.command_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.created_at_ns` | 是 | `{"type": "integer", "minimum": 0}` |
| `$.deadline_ns` | 是 | `{"type": "integer", "minimum": 1}` |
| `$.source_text` | 是 | `{"type": "string", "minLength": 1, "maxLength": 1000}` |
| `$.command_hint` | 否（不等于允许null） | `{"type": "object", "additionalProperties": false, "required": ["intent"]}` |
| `$.command_hint.intent` | 是 | `{"type": "string", "minLength": 1, "maxLength": 64}` |
| `$.command_hint.target_speed_mps` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0}` |
| `$.command_hint.direction` | 否（不等于允许null） | `{"enum": ["LEFT", "RIGHT", "STRAIGHT", null]}` |
| `$.command_hint.target` | 否（不等于允许null） | `{"type": ["string", "null"], "maxLength": 128}` |
| `$.rgb_ref` | 否（不等于允许null） | `{"type": ["string", "null"], "maxLength": 4096}` |
| `$.routing` | 否（不等于允许null） | `{"type": "object", "additionalProperties": false, "required": ["disposition", "score", "reasons", "safe_wait_behavior"]}` |
| `$.routing.disposition` | 是 | `{"enum": ["QWEN_PLAN", "CONFIRM_SAFE"]}` |
| `$.routing.score` | 是 | `{"type": "integer"}` |
| `$.routing.reasons` | 是 | `{"type": "array", "minItems": 1, "uniqueItems": true}` |
| `$.routing.reasons[]` | 数组元素 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.routing.safe_wait_behavior` | 是 | `{"enum": ["KEEP_LANE_LIMITED", "SLOW_DOWN", "STOP", "EMERGENCY_STOP"]}` |
| `$.scene_capabilities` | 否（不等于允许null） | `{"type": "object", "additionalProperties": false}` |
| `$.scene_capabilities.available_lanes` | 否（不等于允许null） | `{"type": "array", "uniqueItems": true}` |
| `$.scene_capabilities.available_lanes[]` | 数组元素 | `{"enum": ["CURRENT", "LEFT_ADJACENT", "RIGHT_ADJACENT", "SHOULDER"]}` |
| `$.scene_capabilities.left_lane_exists` | 否（不等于允许null） | `{"type": "boolean"}` |
| `$.scene_capabilities.right_lane_exists` | 否（不等于允许null） | `{"type": "boolean"}` |
| `$.scene_capabilities.left_gap_safe` | 否（不等于允许null） | `{"type": "boolean"}` |
| `$.scene_capabilities.right_gap_safe` | 否（不等于允许null） | `{"type": "boolean"}` |
| `$.scene_capabilities.route_available` | 否（不等于允许null） | `{"type": "boolean"}` |
| `$.scene_capabilities.intersection_ahead` | 否（不等于允许null） | `{"type": "boolean"}` |
| `$.scene_capabilities.stop_line_clear` | 否（不等于允许null） | `{"type": "boolean"}` |
| `$.scene_capabilities.original_lane` | 否（不等于允许null） | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.scene_capabilities.current_lane` | 否（不等于允许null） | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.scene_capabilities.return_direction` | 否（不等于允许null） | `{"enum": ["LEFT", "RIGHT"]}` |
| `$.scene_capabilities.grounded_target_ids` | 否（不等于允许null） | `{"type": "array", "uniqueItems": true, "maxItems": 8}` |
| `$.scene_capabilities.grounded_target_ids[]` | 数组元素 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.scene_summary` | 是 | `{"type": "object", "additionalProperties": false, "required": ["frame_id", "sim_time_s", "traffic_light", "risk_level"]}` |
| `$.scene_summary.frame_id` | 是 | `{"type": "integer", "minimum": 0}` |
| `$.scene_summary.sim_time_s` | 是 | `{"type": "number", "minimum": 0}` |
| `$.scene_summary.traffic_light` | 是 | `{"enum": ["RED", "YELLOW", "GREEN", "UNKNOWN"]}` |
| `$.scene_summary.risk_level` | 是 | `{"enum": ["LOW", "CAUTION", "HIGH", "EMERGENCY", "UNKNOWN"]}` |
| `$.scene_summary.min_gap_m` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0}` |
| `$.scene_summary.ttc_s` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0}` |
| `$.targets` | 是 | `{"type": "array", "maxItems": 12}` |
| `$.targets[]` | 数组元素 | `{"type": "object", "additionalProperties": false, "required": ["target_id", "class", "distance_m", "confidence", "relation"]}` |
| `$.targets[].target_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.targets[].class` | 是 | `{"enum": ["vehicle", "pedestrian", "cyclist", "obstacle", "unknown"]}` |
| `$.targets[].distance_m` | 是 | `{"type": "number", "minimum": 0}` |
| `$.targets[].relative_speed_mps` | 否（不等于允许null） | `{"type": ["number", "null"]}` |
| `$.targets[].confidence` | 是 | `{"type": "number", "minimum": 0, "maximum": 1}` |
| `$.targets[].relation` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.constraints` | 是 | `{"type": "object", "additionalProperties": false, "required": ["speed_limit_mps", "allowed_behaviors", "must_stop"]}` |
| `$.constraints.speed_limit_mps` | 是 | `{"type": ["number", "null"], "minimum": 0}` |
| `$.constraints.allowed_behaviors` | 是 | `{"type": "array", "minItems": 1, "uniqueItems": true}` |
| `$.constraints.allowed_behaviors[]` | 数组元素 | `{"enum": ["KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP", "YIELD", "FOLLOW", "CHANGE_LANE", "TURN", "AVOID_OBSTACLE", "RETURN_TO_LANE", "PULL_OVER"]}` |
| `$.constraints.must_stop` | 是 | `{"type": "boolean"}` |
| `$.constraints.max_target_speed_mps` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0}` |

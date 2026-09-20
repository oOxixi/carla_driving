# maneuver_plan.schema：功能记录

上级模块：[模块说明](../modules/vehicle-interfaces.md) · 实现：[interfaces/maneuver_plan.schema.json](../../../interfaces/maneuver_plan.schema.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [版本、时间、坐标与适配语义](interface-versioning.md)

## 功能职责与范围

maneuver_plan.schema

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `$schema`：'https://json-schema.org/draft/2020-12/schema'。
- `$id`：'https://carla-driving.local/interfaces/maneuver_plan.schema.json'。
- `title`：'ManeuverPlan V2'。
- `type`：'object'。
- `additionalProperties`：False。
- `required`：列表，共 13 项。
- `properties`：对象，直接字段：schema_version, request_id, command_id, plan_id, plan_type, steps, replan_conditions, confidence, requires_confirmation, created_at_ns, valid_until_ns, reason_code, model_id。
- `$defs`：对象，直接字段：step。

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

### `interfaces/maneuver_plan.schema.json`

来源 SHA256：`fb994ab58e4d44cb33ba10246d83bc8b4e79a4d99cafc3a772c91b4c189ac3df`。


Schema 字段与约束：$ref需解析到对应定义；required只表示本层必填，不能代替分支条件判断。

| 路径 | 必填位置 | 类型/枚举/范围/额外字段策略 |
|---|---|---|
| `$` | 根 | `{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://carla-driving.local/interfaces/maneuver_plan.schema.json", "title": "ManeuverPlan V2", "type": "object", "additionalProperties": false, "required": ["schema_version", "request_id", "command_id", "plan_id", "plan_type", "steps", "replan_conditions", "confidence", "requires_confirmation", "created_at_ns", "valid_until_ns", "reason_code", "model_id"]}` |
| `$.schema_version` | 是 | `{"const": "2.0"}` |
| `$.request_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.command_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.plan_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.plan_type` | 是 | `{"const": "MANEUVER_SEQUENCE"}` |
| `$.steps` | 是 | `{"type": "array", "minItems": 1, "maxItems": 4}` |
| `$.steps[]` | 数组元素 | `{"$ref": "#/$defs/step"}` |
| `$.replan_conditions` | 是 | `{"type": "array", "uniqueItems": true, "maxItems": 8}` |
| `$.replan_conditions[]` | 数组元素 | `{"enum": ["TARGET_LOST", "LANE_BLOCKED", "ROUTE_MISMATCH", "NEW_EMERGENCY_OBJECT", "PROGRESS_STALLED", "ROUTE_DEVIATION", "PLAN_EXPIRING"]}` |
| `$.confidence` | 是 | `{"type": "number", "minimum": 0, "maximum": 1}` |
| `$.requires_confirmation` | 是 | `{"type": "boolean"}` |
| `$.created_at_ns` | 是 | `{"type": "integer", "minimum": 0}` |
| `$.valid_until_ns` | 是 | `{"type": "integer", "minimum": 1}` |
| `$.reason_code` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.model_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 256}` |
| `#/$defs/step` | 引用定义 | `{"type": "object", "additionalProperties": false, "required": ["step_id", "behavior", "target", "preconditions", "completion", "timeout_s", "on_failure"]}` |
| `#/$defs/step.step_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 64}` |
| `#/$defs/step.behavior` | 是 | `{"enum": ["KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP", "YIELD", "FOLLOW", "TURN_LEFT", "TURN_RIGHT", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT", "AVOID_OBSTACLE", "RETURN_TO_LANE", "PULL_OVER", "HOLD"]}` |
| `#/$defs/step.target` | 是 | `{"type": "object", "additionalProperties": false}` |
| `#/$defs/step.target.target_id` | 否（不等于允许null） | `{"type": ["string", "null"], "maxLength": 128}` |
| `#/$defs/step.target.target_lane` | 否（不等于允许null） | `{"enum": ["CURRENT", "LEFT_ADJACENT", "RIGHT_ADJACENT", "ROUTE_BRANCH", "SHOULDER", null]}` |
| `#/$defs/step.target.target_speed_mps` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0, "maximum": 50}` |
| `#/$defs/step.target.time_gap_s` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0.5, "maximum": 10}` |
| `#/$defs/step.target.route_direction` | 否（不等于允许null） | `{"enum": ["LEFT", "RIGHT", "STRAIGHT", null]}` |
| `#/$defs/step.preconditions` | 是 | `{"type": "array", "uniqueItems": true, "maxItems": 8}` |
| `#/$defs/step.preconditions[]` | 数组元素 | `{"enum": ["PERCEPTION_FRESH", "LEFT_LANE_EXISTS", "RIGHT_LANE_EXISTS", "LEFT_GAP_SAFE", "RIGHT_GAP_SAFE", "TARGET_VISIBLE", "ROUTE_AVAILABLE", "INTERSECTION_AHEAD", "STOP_LINE_CLEAR", "NO_EMERGENCY_RISK"]}` |
| `#/$defs/step.completion` | 是 | `{"type": "object", "additionalProperties": false, "required": ["type", "hold_frames"]}` |
| `#/$defs/step.completion.type` | 是 | `{"enum": ["SPEED_BELOW", "SPEED_REACHED", "LANE_CENTERED", "JUNCTION_EXITED", "TARGET_GAP_REACHED", "TARGET_PASSED", "STOPPED", "HOLD_FRAMES"]}` |
| `#/$defs/step.completion.value` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0}` |
| `#/$defs/step.completion.lane` | 否（不等于允许null） | `{"enum": ["CURRENT", "LEFT_ADJACENT", "RIGHT_ADJACENT", "ROUTE_BRANCH", "SHOULDER", null]}` |
| `#/$defs/step.completion.hold_frames` | 是 | `{"type": "integer", "minimum": 1, "maximum": 200}` |
| `#/$defs/step.timeout_s` | 是 | `{"type": "number", "exclusiveMinimum": 0, "maximum": 60}` |
| `#/$defs/step.on_failure` | 是 | `{"enum": ["SAFE_STOP", "HOLD_CURRENT_LANE", "REPLAN", "CONFIRM"]}` |

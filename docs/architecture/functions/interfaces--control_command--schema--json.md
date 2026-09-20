# control_command.schema：功能记录

上级模块：[模块说明](../modules/vehicle-interfaces.md) · 实现：[interfaces/control_command.schema.json](../../../interfaces/control_command.schema.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [版本、时间、坐标与适配语义](interface-versioning.md)

## 功能职责与范围

control_command.schema

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `$schema`：'https://json-schema.org/draft/2020-12/schema'。
- `$id`：'https://carla-driving.local/interfaces/control_command.schema.json'。
- `title`：'Validated ControlCommand V1'。
- `type`：'object'。
- `additionalProperties`：False。
- `required`：列表，共 9 项。
- `properties`：对象，直接字段：schema_version, command_id, path_type, behavior, target, limits, issued_at_ns, deadline_ns, source, confidence, reason_code。
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

### `interfaces/control_command.schema.json`

来源 SHA256：`db60cf6eb12ba29b67e887a8c6c3f9305814d59386a9d2cf963536b4ff51b50b`。


Schema 字段与约束：$ref需解析到对应定义；required只表示本层必填，不能代替分支条件判断。

| 路径 | 必填位置 | 类型/枚举/范围/额外字段策略 |
|---|---|---|
| `$` | 根 | `{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://carla-driving.local/interfaces/control_command.schema.json", "title": "Validated ControlCommand V1", "type": "object", "additionalProperties": false, "required": ["schema_version", "command_id", "path_type", "behavior", "target", "limits", "issued_at_ns", "deadline_ns", "source"], "examples": [{"schema_version": "1.0", "command_id": "voice-0001", "path_type": "SLOW", "behavior": "SET_SPEED", "target": {"target_id": null, "target_speed_mps": 5.5555555556, "time_gap_s": null}, "limits": {"max_speed_mps": 8.3333333333, "max_accel_mps2": 2.5, "max_decel_mps2": 5.0}, "issued_at_ns": 1050000000, "deadline_ns": 4000000000, "source": "QWEN_DECISION_PLAN", "confidence": 0.98, "reason_code": "QWEN_SET_SPEED"}]}` |
| `$.schema_version` | 是 | `{"const": "1.0"}` |
| `$.command_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.path_type` | 是 | `{"const": "SLOW"}` |
| `$.behavior` | 是 | `{"enum": ["KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP", "EMERGENCY_STOP", "YIELD", "FOLLOW", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT", "TURN_LEFT", "TURN_RIGHT", "PULL_OVER", "HOLD"]}` |
| `$.target` | 是 | `{"type": "object", "additionalProperties": false}` |
| `$.target.target_id` | 否（不等于允许null） | `{"type": ["string", "null"], "maxLength": 128}` |
| `$.target.target_speed_mps` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0, "maximum": 50}` |
| `$.target.time_gap_s` | 否（不等于允许null） | `{"type": ["number", "null"], "minimum": 0.5, "maximum": 10}` |
| `$.limits` | 是 | `{"type": "object", "additionalProperties": false, "required": ["max_speed_mps", "max_accel_mps2", "max_decel_mps2"]}` |
| `$.limits.max_speed_mps` | 是 | `{"type": "number", "minimum": 0, "maximum": 50}` |
| `$.limits.max_accel_mps2` | 是 | `{"type": "number", "minimum": 0, "maximum": 10}` |
| `$.limits.max_decel_mps2` | 是 | `{"type": "number", "minimum": 0, "maximum": 15}` |
| `$.issued_at_ns` | 是 | `{"type": "integer", "minimum": 0}` |
| `$.deadline_ns` | 是 | `{"type": "integer", "minimum": 1}` |
| `$.source` | 是 | `{"enum": ["QWEN_DECISION_PLAN", "SAFETY_SYSTEM"]}` |
| `$.confidence` | 否（不等于允许null） | `{"type": "number", "minimum": 0, "maximum": 1}` |
| `$.reason_code` | 否（不等于允许null） | `{"type": "string", "minLength": 1, "maxLength": 128}` |

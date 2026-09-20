# execution_feedback.schema：功能记录

上级模块：[模块说明](../modules/vehicle-interfaces.md) · 实现：[interfaces/execution_feedback.schema.json](../../../interfaces/execution_feedback.schema.json)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [版本、时间、坐标与适配语义](interface-versioning.md)

## 功能职责与范围

execution_feedback.schema

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 维护时要核对的内容

原文件为执行权威；此页不复制整份代码或配置，避免两份正文各自漂移。

- `$schema`：'https://json-schema.org/draft/2020-12/schema'。
- `$id`：'https://carla-driving.local/interfaces/execution_feedback.schema.json'。
- `title`：'ExecutionFeedback V1'。
- `type`：'object'。
- `additionalProperties`：False。
- `required`：列表，共 9 项。
- `properties`：对象，直接字段：schema_version, command_id, status, action_summary, emitted_at_ns, t_action_apply_ns, latency_ms, safety_event, terminal_reason。
- `$defs`：对象，直接字段：vehicle_control。
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

### `interfaces/execution_feedback.schema.json`

来源 SHA256：`a727000e618e0d5f2b08318352f679f02a65dbe16f674e748f06aa121b444d2b`。


Schema 字段与约束：$ref需解析到对应定义；required只表示本层必填，不能代替分支条件判断。

| 路径 | 必填位置 | 类型/枚举/范围/额外字段策略 |
|---|---|---|
| `$` | 根 | `{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://carla-driving.local/interfaces/execution_feedback.schema.json", "title": "ExecutionFeedback V1", "type": "object", "additionalProperties": false, "required": ["schema_version", "command_id", "status", "action_summary", "emitted_at_ns", "t_action_apply_ns", "latency_ms", "safety_event", "terminal_reason"], "examples": [{"schema_version": "1.0", "command_id": "voice-0001", "status": "SUCCEEDED", "action_summary": "target speed reached and settled", "emitted_at_ns": 1800000000, "t_action_apply_ns": 1100000000, "latency_ms": 100.0, "safety_event": null, "terminal_reason": "TARGET_REACHED"}]}` |
| `$.schema_version` | 是 | `{"const": "1.0"}` |
| `$.command_id` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.status` | 是 | `{"enum": ["RECEIVED", "EXECUTING", "SUCCEEDED", "FAILED", "REJECTED", "EXPIRED", "TIMED_OUT", "SAFETY_OVERRIDE"]}` |
| `$.action_summary` | 是 | `{"type": "string", "minLength": 1, "maxLength": 1000}` |
| `$.emitted_at_ns` | 是 | `{"type": "integer", "minimum": 0}` |
| `$.t_action_apply_ns` | 是 | `{"type": ["integer", "null"], "minimum": 0}` |
| `$.latency_ms` | 是 | `{"type": ["number", "null"], "minimum": 0}` |
| `$.safety_event` | 是 | `{"type": ["object", "null"], "additionalProperties": false, "required": ["reason_code", "raw_control", "final_control"]}` |
| `$.safety_event.reason_code` | 是 | `{"type": "string", "minLength": 1, "maxLength": 128}` |
| `$.safety_event.raw_control` | 是 | `{"$ref": "#/$defs/vehicle_control"}` |
| `$.safety_event.final_control` | 是 | `{"$ref": "#/$defs/vehicle_control"}` |
| `$.terminal_reason` | 是 | `{"type": ["string", "null"], "maxLength": 1000}` |
| `#/$defs/vehicle_control` | 引用定义 | `{"type": "object", "additionalProperties": false, "required": ["throttle", "brake", "steer"]}` |
| `#/$defs/vehicle_control.throttle` | 是 | `{"type": "number", "minimum": 0, "maximum": 1}` |
| `#/$defs/vehicle_control.brake` | 是 | `{"type": "number", "minimum": 0, "maximum": 1}` |
| `#/$defs/vehicle_control.steer` | 是 | `{"type": "number", "minimum": -1, "maximum": 1}` |
